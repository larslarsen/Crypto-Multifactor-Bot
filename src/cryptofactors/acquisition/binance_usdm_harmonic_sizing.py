"""CEX-002 ADR-0021 — bounded real-sample storage sizing for the Harmonic release.

This probe answers one question from measured evidence: how much durable storage the
accepted Gate-1 release needs before Gate 2 may be considered. It reads only the accepted
local authority, measures only real retained bytes, projects with integer rational
arithmetic, and publishes only its own evidence.

What it refuses matters as much as what it does. It performs no network call, needs no
credential, and accepts no caller-selected cohort, family, coefficient, multiplicity,
compression, batch size, overhead, credit, reserve, lifecycle, Coinalyze evidence, or
capacity. Every policy input comes from review 179/181 pins or from the accepted report
itself. A `sufficient` preflight is a storage measurement, never an authorization.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import re
import struct
import tempfile
import zipfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    COINALYZE_EXCHANGE_CODE,
    KNOWN_ARCHIVE_SCHEMAS,
    RetainedChecksumIndex,
    compute_sha256,
    file_sha256,
    parse_s3_list_bucket,
    verify_provider_sidecar,
    verify_retained_object,
)

TICKET_ID: str = "CEX-002"
SIZING_SCHEMA_VERSION: str = "cex002_gate2_storage_sizing_v2"
SIZING_POLICY_IDENTITY: str = (
    "adr0024_review230_typed_product_real_partition_atomic_storage_sizing_v2"
)

# --- pinned accepted authority (reviews 179 and 181) -----------------------------------

ACCEPTED_REPORT_SHA256: str = (
    "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
)
ACCEPTED_REPORT_BYTES: int = 13_745_360
ACCEPTED_MANIFEST_DETAIL_SHA256: str = (
    "64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113"
)
ACCEPTED_MANIFEST_DETAIL_BYTES: int = 11_292_635
ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_SHA256: str = (
    "d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17"
)
ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_BYTES: int = 466_714_158
ACCEPTED_LOCK_SHA256: str = (
    "6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e"
)
ACCEPTED_AMENDMENT_LEDGER_SHA256: str = (
    "2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf"
)
ACCEPTED_QUALIFICATION_SOURCE_SHA256: str = (
    "2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74"
)
ACCEPTED_QUALIFICATION_CLI_SHA256: str = (
    "473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f"
)
ACCEPTED_PROGRESS_CHECKPOINT_SHA256: str = (
    "cc8e02389d182e6d76d00b913503d95f72a352d883c50ffd81dd3c49df157b2f"
)
ACCEPTED_LISTING_CHECKPOINT_SHA256: str = (
    "d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a"
)
ACCEPTED_CONTRACT_METADATA_SHA256: str = (
    "7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42"
)

ACCEPTED_PLAN_VERSION: int = 4
ACCEPTED_PLAN_ENTRIES: int = 106
ACCEPTED_PLAN_ACTIONS: Mapping[str, int] = {
    "download": 84,
    "reuse_retained": 12,
    "alias": 10,
}
ACCEPTED_SAMPLE_COHORT: int = 96

# The exact physical input the accepted release must acquire, before any projection.
ACCEPTED_SELECTED_OBJECTS: int = 733_203
ACCEPTED_SELECTED_BYTES: int = 7_833_966_625
ACCEPTED_COST_OBJECTS: int = 3_144
ACCEPTED_COST_BYTES: int = 12_522_974_218
ACCEPTED_COMBINED_OBJECTS: int = 736_347
ACCEPTED_COMBINED_BYTES: int = 20_356_940_843
ACCEPTED_RETAINED_CREDIT_OBJECTS: int = 73
ACCEPTED_RETAINED_CREDIT_BYTES: int = 5_225_416
# ADR-0022 separates logical keys from unique physical objects, and ADR-0023 fixes the
# split: 68 selected retained keys plus 5 cost retained keys are the 73 valid Gate-2
# requirement keys. The sizing consumer must reproduce this before measuring.
ACCEPTED_RETAINED_CREDIT_KEYS: int = 73
ACCEPTED_SELECTED_RETAINED_KEYS: int = 68
ACCEPTED_COST_RETAINED_KEYS: int = 5
# ADR-0023: manifest consumability is a separate publication fact with its own boundary.
# It is never the Gate-2 credit set, and neither side of the credit split may be inferred
# by subtracting it from the credit total.
ACCEPTED_MANIFEST_CONSUMABLE_ROWS: int = 56
ACCEPTED_REJECTED_RECOVERED_ROWS: int = 176
ACCEPTED_UNVERIFIED_RETAINED_OBJECTS: int = 0
ACCEPTED_NEW_BINANCE_RAW_BYTES: int = 20_351_715_427
ACCEPTED_LARGEST_SELECTED_OBJECT_BYTES: int = 200_457_493
ACCEPTED_COINALYZE_SUPPORTED_MAPPINGS: int = 569
ACCEPTED_COINALYZE_TYPED_GAPS: int = 202
ACCEPTED_COINALYZE_PROVENANCE_RECORDS: int = 5
# ADR-0025 section 4: the accepted report carries 106 logical sample records over 96
# unique physical keys. Ten keys appear twice under different logical regime roles with
# identical lineage; those aliases fold, and only a disagreement blocks.
ACCEPTED_LOGICAL_SAMPLE_RECORDS: int = 106
ACCEPTED_PHYSICAL_SAMPLE_BINDINGS: int = 96
ACCEPTED_FOLDED_SAMPLE_ALIASES: int = 10
# ADR-0025 section 6 and ADR-0026 section 5: the known coverage minimum.
# The pinned report carries every classified name, accepted or not. Only the accepted
# identities are release membership; the rest are proved exclusion evidence.
ACCEPTED_MEMBERSHIP_CLASSIFICATIONS: int = 1_008
ACCEPTED_MEMBERSHIP_IDENTITIES: int = 771
ACCEPTED_REJECTED_MEMBERSHIP_ROWS: int = 237
ACCEPTED_DETAILED_MEMBERSHIP_IDENTITIES: int = 698
ACCEPTED_FUNDING_ONLY_MEMBERSHIP_IDENTITIES: int = 73
MEMBERSHIP_ACCEPTED_CLASS: str = "confirmed_perpetual"
# REF-001 canonical identities are opaque fingerprints created by the reference store.
# No Gate-1 artifact has created them yet, so sizing allocates their exact encoded width
# as a future Gate-3 schema charge and never publishes a ticker-derived stand-in.
REF_INSTRUMENT_ID_WIDTH: int = 68
REF_INSTRUMENT_VERSION_ID_WIDTH: int = 67
REF_IDENTITY_STATE: str = "reference_identity_not_yet_created"
SHA256_WIDTH: int = 64
FUTURE_TIMESTAMP_WIDTH: int = 32
INTEGER_WIDTH: int = 8
DICTIONARY_INDEX_WIDTH: int = 4
VARIABLE_OFFSET_WIDTH: int = 4
NULL_VALIDITY_WIDTH: int = 1
MEMBERSHIP_DETAILED_STATE: str = "exchange_info_terms_available"
MEMBERSHIP_FUNDING_ONLY_STATE: str = "funding_only_terms_unavailable"
FUNDING_ONLY_EVIDENCE_CLASS: str = "official_realized_funding_observation"
FUNDING_ONLY_SEMANTICS: str = "only a perpetual contract realizes funding"
PROJECTED_UNACQUIRED_STATE: str = "projected_unacquired"
RETAINED_RECEIPT_STATE: str = "retained_verified_receipt"
ACCEPTED_SOURCE_COVERAGE_GAPS: int = 8_317
ACCEPTED_TYPED_GAP_MEMBERSHIPS: int = 3_742
ACCEPTED_FEE_AUTHORITY_GAPS: int = 771
ACCEPTED_KNOWN_COVERAGE_ROWS: int = 9_088
# ADR-0026: no free reproducible historical fee authority exists for this interval.
ACCEPTED_OFFICIAL_FEE_ROWS: int = 0
FEE_AUTHORITY_CLASS: str = "ASSUMED_CONSERVATIVE"
FEE_GAP_KIND: str = "historical_fee_schedule_unavailable"
FEE_POLICY_KNOWN_AT: str = "2026-08-23T03:00:00Z"
FEE_SCENARIO_SCOPE: str = "binance_usdm_perpetual_execution"
# Outcome-blind configuration rows, not FEE-001 historical observations. Neither claims a
# past Binance rate, and neither may be inserted with a backdated availability time.
FEE_SCENARIOS: tuple[Mapping[str, str], ...] = (
    {
        "scenario_id": "assumed_conservative_5bps_per_side_v1",
        "maker_rate": "0.0005",
        "taker_rate": "0.0005",
        "role": "primary_assumption",
    },
    {
        "scenario_id": "assumed_severe_10bps_per_side_v1",
        "maker_rate": "0.0010",
        "taker_rate": "0.0010",
        "role": "required_sensitivity",
    },
)
# The exact accepted provenance record shape. Qualification publishes sorted header
# *names* and never a header value, so the name is safe metadata while any field outside
# this set could carry a header value, authorization data, or another secret.
ACCEPTED_COINALYZE_PROVENANCE_FIELDS: frozenset[str] = frozenset(
    {
        "byte_size",
        "content_path",
        "header_names",
        "params",
        "path",
        "provenance_source",
        "retrieved_at",
        "sha256",
        "status_code",
        "transport",
    }
)
ACCEPTED_COINALYZE_HEADER_NAMES: tuple[str, ...] = ("api_key",)
# A query parameter may never name a credential under any spelling. Names are normalized
# by case and by dropping "_" and "-" before this comparison.
CREDENTIAL_PARAMETER_MARKERS: tuple[str, ...] = (
    "apikey",
    "authorization",
    "secret",
    "token",
)

# --- ADR-0021 fixed contract -----------------------------------------------------------

SIZING_ROW_BATCH: int = 65_536
CATALOG_PAGE_BYTES: int = 4_096
MINIMUM_OPERATING_RESERVE_BYTES: int = 16 * 2**30
RESERVE_DIVISOR: int = 5
PARQUET_COMPRESSION: str = "zstd"
PARQUET_COMPRESSION_LEVEL: int = 3
PARQUET_VERSION: str = "2.6"
PARQUET_TRAILER_BYTES: int = 8
PARQUET_MAGIC_BYTES: int = 4

# The 10 selected archive families, then the two cost families. Together they are the 12
# physical families ADR-0021 requires, but they arrive from two different authorities.
ARCHIVE_FAMILIES: tuple[str, ...] = (
    "daily/klines",
    "daily/metrics",
    "daily/premiumIndexKlines",
    "daily/markPriceKlines",
    "daily/indexPriceKlines",
    "monthly/klines",
    "monthly/fundingRate",
    "monthly/premiumIndexKlines",
    "monthly/markPriceKlines",
    "monthly/indexPriceKlines",
)
COST_FAMILIES: tuple[str, ...] = ("daily/bookTicker", "daily/bookDepth")
PHYSICAL_FAMILIES: tuple[str, ...] = ARCHIVE_FAMILIES + COST_FAMILIES

# Fixed logical fan-out. These come only from ADR-0021; no caller may change them.
OUTPUT_MULTIPLICITY: Mapping[str, int] = {
    "daily/klines": 2,
    "monthly/klines": 2,
    "daily/metrics": 1,
    "monthly/fundingRate": 1,
    "daily/premiumIndexKlines": 2,
    "monthly/premiumIndexKlines": 2,
    "daily/markPriceKlines": 1,
    "monthly/markPriceKlines": 1,
    "daily/indexPriceKlines": 1,
    "monthly/indexPriceKlines": 1,
    "daily/bookTicker": 1,
    "daily/bookDepth": 1,
}
COINALYZE_LIQUIDATION_MULTIPLICITY: int = 1
COINALYZE_LIQUIDATION_ENDPOINT: str = "/liquidation-history"
COINALYZE_MARKETS_ENDPOINT: str = "/future-markets"
COINALYZE_OVERLAP_ENDPOINTS: tuple[str, ...] = (
    "/open-interest-history",
    "/funding-rate-history",
    "/ohlcv-history",
)

SIZING_EVIDENCE_ROOT: str = "evidence/sizing/v2/envelopes/sha256"
SIZING_RECEIPT_RELATIVE_PATH: str = (
    "research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json"
)
# The accepted version-1 diagnosis. It and its 98 envelopes are immutable blocked
# evidence: version 2 reads neither and writes to neither, ever.
V1_SIZING_EVIDENCE_ROOT: str = "evidence/sizing/v1/envelopes/sha256"
V1_SIZING_RECEIPT_RELATIVE_PATH: str = (
    "research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json"
)
V1_ACCEPTED_RECEIPT_SHA256: str = (
    "f2e1fef8156e3af1abd40554e5a8393ee6566e1719cf990a2a49867e5aef185c"
)
STATE_SUFFICIENT: str = "sufficient"
STATE_BLOCKED: str = "blocked"

BLOCKER_AUTHORITY: str = "accepted_authority_mismatch"
BLOCKER_INPUTS: str = "physical_input_reconciliation_failed"
BLOCKER_COHORT: str = "sample_cohort_incomplete"
BLOCKER_COINALYZE: str = "coinalyze_projection_incomplete"
BLOCKER_CAPACITY: str = "available_capacity_insufficient"
BLOCKER_UNKNOWN: str = "component_unknown_or_non_integer"
BLOCKER_TYPED: str = "typed_normalization_incomplete"


class SizingError(RuntimeError):
    """A sizing precondition failed. Nothing is measured or published on this path."""

    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(payload: Mapping[str, Any]) -> bytes:
    """The one canonical serialization used for every durable receipt byte."""
    return (json.dumps(dict(payload), indent=2, sort_keys=True) + "\n").encode("utf-8")


def requirement_key_set_sha256(keys: Sequence[str]) -> str:
    """Deterministic identity of one exact set of full requirement keys."""
    normalized = sorted(str(key) for key in keys)
    _require(
        len(set(normalized)) == len(normalized),
        "a requirement key set contains a duplicate full key",
        {"keys": len(normalized)},
    )
    return _sha256_bytes(canonical_json({"requirement_keys": normalized}))


def _require(condition: bool, message: str, context: Mapping[str, Any]) -> None:
    if not condition:
        raise SizingError(message, context=dict(context))


def _exact(
    actual: Any, expected: Any, *, field_name: str, context: Mapping[str, Any]
) -> None:
    if actual != expected:
        raise SizingError(
            "accepted sizing authority does not match its pinned identity",
            context={
                **dict(context),
                "field": field_name,
                "actual": actual,
                "expected": expected,
            },
        )


def _positive_int(value: Any, *, field_name: str, context: Mapping[str, Any]) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SizingError(
            "sizing component is not a positive integer",
            context={**dict(context), "field": field_name, "value": value},
        )
    return value


def ceil_div(numerator: int, denominator: int) -> int:
    """Integer ceiling division. No float ever touches a projected byte count."""
    if isinstance(numerator, bool) or isinstance(denominator, bool):
        raise SizingError("projection operands must be integers", context={})
    if not isinstance(numerator, int) or not isinstance(denominator, int):
        raise SizingError("projection operands must be integers", context={})
    if denominator <= 0:
        raise SizingError("projection denominator must be positive", context={})
    if numerator < 0:
        raise SizingError("projection numerator must be non-negative", context={})
    return -(-numerator // denominator)


def ratio_exceeds(
    left: tuple[int, int], right: tuple[int, int]
) -> bool:
    """Compare two exact rationals by cross multiplication. No division, no float."""
    left_num, left_den = left
    right_num, right_den = right
    _positive_int(left_den, field_name="denominator", context={})
    _positive_int(right_den, field_name="denominator", context={})
    return left_num * right_den > right_num * left_den


def utc_month(value: str) -> str:
    """The UTC month a source key's economic interval belongs to."""
    text = str(value)
    return text[:7] if len(text) >= 7 else text


# --- accepted authority ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SizingAuthority:
    """Every accepted artifact this probe is pinned to, already re-proved."""

    store_root: Path
    report_path: Path
    report: Mapping[str, Any]
    manifest_detail_path: Path
    listing_checkpoint: Mapping[str, Any]
    progress_checkpoint: Mapping[str, Any]
    contract_metadata: Mapping[str, Any]
    lock: Mapping[str, Any]
    amendment_ledger: Mapping[str, Any]
    plan_entries: tuple[Mapping[str, Any], ...]
    bindings: Mapping[str, str]


def _load_json(path: Path, *, label: str) -> Mapping[str, Any]:
    _require(path.is_file(), f"the accepted {label} is missing", {"path": str(path)})
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SizingError(
            f"the accepted {label} is not JSON", context={"path": str(path)}
        ) from exc
    _require(
        isinstance(document, dict),
        f"the accepted {label} is not an object",
        {"path": str(path)},
    )
    return document


@dataclass(frozen=True, slots=True)
class AuthorityPaths:
    """Where the accepted bytes live. Locations only; identities are pinned."""

    store_root: Path
    report_path: Path
    manifest_detail_path: Path
    qualification_source_path: Path
    qualification_cli_path: Path
    lock_path: Path
    amendment_ledger_path: Path
    progress_checkpoint_path: Path
    listing_checkpoint_path: Path
    contract_metadata_path: Path
    listing_cache_dir: Path
    coinalyze_cache_dir: Path
    sample_dir: Path
    sidecar_dir: Path


def load_sizing_authority(paths: AuthorityPaths) -> SizingAuthority:
    """Re-prove every accepted artifact before a single byte is measured.

    A matching report hash is not sufficient on its own: the report's own version-4 plan,
    plan digest, code/config digest, source receipt, lock, ledger, manifest-detail, and
    source-identity bindings must all agree with the artifacts on disk, and the accepted
    checkpoints and official metadata must rehash to their pinned identities.
    """
    context = {"store_root": str(paths.store_root)}
    pinned: tuple[tuple[Path, str, int | None, str], ...] = (
        (paths.report_path, ACCEPTED_REPORT_SHA256, ACCEPTED_REPORT_BYTES, "report"),
        (
            paths.manifest_detail_path,
            ACCEPTED_MANIFEST_DETAIL_SHA256,
            ACCEPTED_MANIFEST_DETAIL_BYTES,
            "manifest detail",
        ),
        (paths.lock_path, ACCEPTED_LOCK_SHA256, None, "version-4 lock"),
        (
            paths.amendment_ledger_path,
            ACCEPTED_AMENDMENT_LEDGER_SHA256,
            None,
            "amendment ledger",
        ),
        (
            paths.qualification_source_path,
            ACCEPTED_QUALIFICATION_SOURCE_SHA256,
            None,
            "qualification production source",
        ),
        (
            paths.qualification_cli_path,
            ACCEPTED_QUALIFICATION_CLI_SHA256,
            None,
            "qualification CLI",
        ),
        (
            paths.progress_checkpoint_path,
            ACCEPTED_PROGRESS_CHECKPOINT_SHA256,
            None,
            "qualification progress checkpoint",
        ),
        (
            paths.listing_checkpoint_path,
            ACCEPTED_LISTING_CHECKPOINT_SHA256,
            None,
            "listing checkpoint",
        ),
        (
            paths.contract_metadata_path,
            ACCEPTED_CONTRACT_METADATA_SHA256,
            None,
            "official contract metadata",
        ),
    )
    for path, digest, size, label in pinned:
        _require(
            path.is_file(), f"the accepted {label} is missing", {"path": str(path)}
        )
        _exact(file_sha256(path), digest, field_name=f"{label}_sha256", context=context)
        if size is not None:
            _exact(
                int(path.stat().st_size),
                size,
                field_name=f"{label}_bytes",
                context=context,
            )

    report = _load_json(paths.report_path, label="report")
    lock = _load_json(paths.lock_path, label="version-4 lock")
    ledger = _load_json(paths.amendment_ledger_path, label="amendment ledger")
    listing = _load_json(paths.listing_checkpoint_path, label="listing checkpoint")
    progress = _load_json(
        paths.progress_checkpoint_path, label="qualification progress checkpoint"
    )
    metadata = _load_json(
        paths.contract_metadata_path, label="official contract metadata"
    )

    plan_lock = report.get("plan_lock")
    _require(
        isinstance(plan_lock, dict), "the accepted report has no plan lock", context
    )
    _exact(
        plan_lock.get("plan_version"),
        ACCEPTED_PLAN_VERSION,
        field_name="report.plan_version",
        context=context,
    )
    _exact(
        lock.get("plan_version"),
        ACCEPTED_PLAN_VERSION,
        field_name="lock.plan_version",
        context=context,
    )
    _exact(
        plan_lock.get("plan_digest"),
        lock.get("plan_digest"),
        field_name="report.plan_digest",
        context=context,
    )
    lock_inputs = dict(lock.get("inputs") or {})
    _exact(
        dict(plan_lock.get("inputs") or {}),
        lock_inputs,
        field_name="report.plan_inputs",
        context=context,
    )
    snapshot = dict(lock.get("budget_snapshot") or {})
    binding = dict(snapshot.get("amendment_binding") or {})
    _exact(
        binding,
        dict(ledger.get("binding") or {}),
        field_name="lock.amendment_binding",
        context=context,
    )
    receipts = list(binding.get("source_receipts") or ())
    _require(
        bool(receipts), "the amendment ledger carries no source receipt", context
    )
    identity = dict(receipts[-1].get("source_identity") or {})
    _exact(
        identity.get("code_config_digest"),
        lock_inputs.get("code_config_digest"),
        field_name="ledger.source_receipt_code_config_digest",
        context=context,
    )
    _exact(
        identity.get("module_sha256"),
        ACCEPTED_QUALIFICATION_SOURCE_SHA256,
        field_name="ledger.source_receipt_module_sha256",
        context=context,
    )
    detail = dict(dict(report.get("acquisition_manifest") or {}).get("detail") or {})
    _exact(
        detail.get("compressed_sha256"),
        ACCEPTED_MANIFEST_DETAIL_SHA256,
        field_name="report.manifest_detail_compressed_sha256",
        context=context,
    )
    _exact(
        detail.get("uncompressed_sha256"),
        ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_SHA256,
        field_name="report.manifest_detail_uncompressed_sha256",
        context=context,
    )
    _exact(
        detail.get("uncompressed_bytes"),
        ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_BYTES,
        field_name="report.manifest_detail_uncompressed_bytes",
        context=context,
    )
    entries = tuple(
        dict(item) for item in (lock.get("plan") or {}).get("entries") or ()
    )
    _exact(
        len(entries), ACCEPTED_PLAN_ENTRIES, field_name="lock.plan_entries", context=context
    )
    return SizingAuthority(
        store_root=paths.store_root,
        report_path=paths.report_path,
        report=report,
        manifest_detail_path=paths.manifest_detail_path,
        listing_checkpoint=listing,
        progress_checkpoint=progress,
        contract_metadata=metadata,
        lock=lock,
        amendment_ledger=ledger,
        plan_entries=entries,
        bindings={
            "report_sha256": ACCEPTED_REPORT_SHA256,
            "manifest_detail_sha256": ACCEPTED_MANIFEST_DETAIL_SHA256,
            "manifest_detail_uncompressed_sha256": (
                ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_SHA256
            ),
            "lock_sha256": ACCEPTED_LOCK_SHA256,
            "amendment_ledger_sha256": ACCEPTED_AMENDMENT_LEDGER_SHA256,
            "qualification_source_sha256": ACCEPTED_QUALIFICATION_SOURCE_SHA256,
            "qualification_cli_sha256": ACCEPTED_QUALIFICATION_CLI_SHA256,
            "progress_checkpoint_sha256": ACCEPTED_PROGRESS_CHECKPOINT_SHA256,
            "listing_checkpoint_sha256": ACCEPTED_LISTING_CHECKPOINT_SHA256,
            "contract_metadata_sha256": ACCEPTED_CONTRACT_METADATA_SHA256,
            "plan_digest": str(lock.get("plan_digest") or ""),
            "code_config_digest": str(lock_inputs.get("code_config_digest") or ""),
        },
    )


# --- exact physical inputs -------------------------------------------------------------


def _family_of(key: str) -> str:
    for family in PHYSICAL_FAMILIES:
        cadence, _, name = family.partition("/")
        if f"/{cadence}/{name}/" in key:
            return family
    return ""


def _economic_interval(key: str) -> str:
    stem = key.rsplit("/", 1)[-1]
    stem = stem[: -len(".zip")] if stem.endswith(".zip") else stem
    parts = stem.split("-")
    return "-".join(parts[-3:]) if len(parts) >= 3 else stem


def _symbol_of(key: str, family: str) -> str:
    cadence, _, name = family.partition("/")
    marker = f"/{cadence}/{name}/"
    tail = key.split(marker, 1)[1] if marker in key else ""
    return tail.split("/", 1)[0] if tail else ""


@dataclass(frozen=True, slots=True)
class PhysicalObject:
    """One exact physical object the accepted release must acquire."""

    key: str
    family: str
    symbol: str
    economic_interval: str
    byte_size: int
    consumable: bool = False


def resolve_selected_objects(
    manifest_detail_path: Path,
) -> tuple[tuple[PhysicalObject, ...], dict[str, Any]]:
    """Stream the accepted manifest detail and re-prove both of its identities.

    The selected rows are the ten archive families. The two cost families deliberately
    live in the report's complete cost manifest instead, so they are resolved separately
    rather than silently expected here.
    """
    context = {"path": str(manifest_detail_path)}
    _exact(
        file_sha256(manifest_detail_path),
        ACCEPTED_MANIFEST_DETAIL_SHA256,
        field_name="manifest_detail_compressed_sha256",
        context=context,
    )
    digest = hashlib.sha256()
    uncompressed = 0
    records = 0
    rows: list[PhysicalObject] = []
    with gzip.open(manifest_detail_path, "rb") as handle:
        for raw in handle:
            digest.update(raw)
            uncompressed += len(raw)
            records += 1
            record = json.loads(raw.decode("utf-8"))
            if str(record.get("record_type")) != "row":
                continue
            row = record.get("record") or {}
            key = str(row.get("key") or "")
            family = str(row.get("family") or "")
            _require(
                family in ARCHIVE_FAMILIES,
                "a selected manifest row is outside the archive families",
                {**context, "family": family},
            )
            size = row.get("byte_size")
            _require(
                isinstance(size, int) and not isinstance(size, bool) and size > 0,
                "a selected manifest row has no positive integer size",
                {**context, "key": key},
            )
            rows.append(
                PhysicalObject(
                    key=key,
                    family=family,
                    symbol=str(row.get("symbol") or ""),
                    economic_interval=str(row.get("economic_interval") or ""),
                    byte_size=int(size),
                    # The manifest's own publication fact. ADR-0023 keeps it separate
                    # from Gate-2 retained credit, which is re-proved independently.
                    consumable=row.get("consumable") is True,
                )
            )
    _exact(
        digest.hexdigest(),
        ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_SHA256,
        field_name="manifest_detail_uncompressed_sha256",
        context=context,
    )
    _exact(
        uncompressed,
        ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_BYTES,
        field_name="manifest_detail_uncompressed_bytes",
        context=context,
    )
    _exact(
        len(rows),
        ACCEPTED_SELECTED_OBJECTS,
        field_name="selected_object_count",
        context=context,
    )
    total = sum(item.byte_size for item in rows)
    _exact(
        total, ACCEPTED_SELECTED_BYTES, field_name="selected_bytes", context=context
    )
    consumable_rows = sum(1 for item in rows if item.consumable)
    _exact(
        consumable_rows,
        ACCEPTED_MANIFEST_CONSUMABLE_ROWS,
        field_name="manifest_consumable_rows",
        context=context,
    )
    return tuple(rows), {
        "record_count": records,
        "row_count": len(rows),
        "compressed_bytes": ACCEPTED_MANIFEST_DETAIL_BYTES,
        "uncompressed_bytes": uncompressed,
        "selected_bytes": total,
        # Published separately from every Gate-2 credit quantity.
        "manifest_consumable_rows": consumable_rows,
    }


def resolve_cost_objects(
    authority: SizingAuthority, *, listing_cache_dir: Path
) -> tuple[tuple[PhysicalObject, ...], dict[str, Any]]:
    """Resolve every accepted cost key's exact size from retained listing evidence.

    Sizes are read from the same content-addressed listing responses the qualification
    bound in its checkpoint, each rehashed here. Nothing is downloaded and no size is
    inferred: a cost key the accepted listings do not carry blocks.
    """
    context = {"listing_cache_dir": str(listing_cache_dir)}
    storage = dict(authority.report.get("storage") or {})
    cost_block = dict(storage.get("cost_sample") or {})
    keys = [str(item) for item in (cost_block.get("keys") or ())]
    _exact(
        len(keys), ACCEPTED_COST_OBJECTS, field_name="cost_key_count", context=context
    )
    entries = dict(authority.listing_checkpoint.get("entries") or {})
    _require(bool(entries), "the accepted listing checkpoint has no entries", context)
    sizes: dict[str, int] = {}
    used: dict[str, str] = {}
    wanted = set(keys)
    for name, entry in sorted(entries.items()):
        if not isinstance(entry, dict):
            continue
        content_path = Path(str(entry.get("content_path") or ""))
        digest = str(entry.get("response_sha256") or "")
        if not content_path.is_file() or not digest:
            continue
        resolved = content_path.resolve()
        _require(
            resolved.parent == Path(listing_cache_dir).resolve(),
            "a listing response escapes the accepted cache",
            {**context, "path": str(content_path)},
        )
        actual = compute_sha256(content_path)
        _exact(
            actual, digest, field_name=f"listing_response_sha256[{name}]", context=context
        )
        body = content_path.read_bytes()
        try:
            _prefixes, listed, _truncated, _token = parse_s3_list_bucket(
                body.decode("utf-8")
            )
        except Exception:  # noqa: BLE001 - a malformed listing is simply not usable here
            continue
        for obj in listed:
            key = str(obj.key)
            if key in wanted and key not in sizes:
                size = obj.size
                _require(
                    isinstance(size, int) and not isinstance(size, bool) and size > 0,
                    "an accepted cost key has no positive listed size",
                    {**context, "key": key},
                )
                sizes[key] = int(size)
                used[key] = actual
    missing = sorted(key for key in keys if key not in sizes)
    _require(
        not missing,
        "the accepted listing evidence does not size every cost key",
        {**context, "missing": missing[:8], "missing_count": len(missing)},
    )
    objects: list[PhysicalObject] = []
    for key in sorted(keys):
        family = _family_of(key)
        _require(
            family in COST_FAMILIES,
            "an accepted cost key is outside the cost families",
            {**context, "key": key},
        )
        objects.append(
            PhysicalObject(
                key=key,
                family=family,
                symbol=_symbol_of(key, family),
                economic_interval=_economic_interval(key),
                byte_size=sizes[key],
            )
        )
    total = sum(item.byte_size for item in objects)
    _exact(total, ACCEPTED_COST_BYTES, field_name="cost_bytes", context=context)
    return tuple(objects), {
        "cost_object_count": len(objects),
        "cost_bytes": total,
        "listing_responses_used": len(set(used.values())),
    }


# The report's own retained summary, and the accepted constant each field must equal.
ACCEPTED_RETAINED_SUMMARY_FIELDS: Mapping[str, str] = {
    "retained_valid_requirement_keys": "ACCEPTED_RETAINED_CREDIT_KEYS",
    "retained_verified_credit_objects": "ACCEPTED_RETAINED_CREDIT_OBJECTS",
    "retained_verified_credit_bytes": "ACCEPTED_RETAINED_CREDIT_BYTES",
    "unverified_retained_objects": "ACCEPTED_UNVERIFIED_RETAINED_OBJECTS",
    "rejected_retained_row_count": "ACCEPTED_REJECTED_RECOVERED_ROWS",
}


def prove_report_retained_summary(report: Mapping[str, Any]) -> dict[str, int]:
    """Prove the pinned report's own retained summary against the accepted constants.

    The report is hash-pinned, but the digest alone leaves the values this consumer acts
    on invisible. Each accepted retained quantity is therefore compared field by field
    before any retained proof or envelope publication, so an altered summary blocks on
    its own name rather than only through a whole-artifact digest.
    """
    context = {"source": "report.storage.gate2_feasibility"}
    feasibility = dict(dict(report.get("storage") or {}).get("gate2_feasibility") or {})
    summary: dict[str, int] = {}
    for field, constant in ACCEPTED_RETAINED_SUMMARY_FIELDS.items():
        value = feasibility.get(field)
        _require(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0,
            "the report's retained summary field is not a non-negative integer",
            {**context, "field": field, "value": value},
        )
        _exact(
            int(value),
            globals()[constant],
            field_name=f"gate2_feasibility.{field}",
            context=context,
        )
        summary[field] = int(value)
    # Unique objects can never exceed the logical keys that bind them.
    _require(
        summary["retained_verified_credit_objects"]
        <= summary["retained_valid_requirement_keys"],
        "the report credits more retained objects than it has valid keys",
        {**context, **summary},
    )
    return summary


def report_rejected_retained_keys(report: Mapping[str, Any]) -> tuple[str, ...]:
    """The report's declared rejected rows, proved consistent across both locations.

    The corrected qualification report names the ADR-0022 rejected legacy rows in two
    places: the resume evidence key list and the Gate-2 feasibility row records. They are
    one fact, so a disagreement between them blocks rather than picking a winner.
    """
    context = {"source": "report"}
    resume = dict(report.get("resume") or {})
    resume_keys = tuple(
        str(item) for item in (resume.get("rejected_ambiguous_retained_keys") or ())
    )
    feasibility = dict(dict(report.get("storage") or {}).get("gate2_feasibility") or {})
    row_keys = tuple(
        str(dict(item).get("key") or "")
        for item in (feasibility.get("rejected_retained_rows") or ())
    )
    if sorted(resume_keys) != sorted(row_keys):
        raise SizingError(
            "the report's two rejected-retained locations disagree",
            context={
                **context,
                "resume_only": sorted(set(resume_keys) - set(row_keys))[:8],
                "rows_only": sorted(set(row_keys) - set(resume_keys))[:8],
            },
        )
    _exact(
        int(resume.get("rejected_ambiguous_retained_count") or -1),
        len(resume_keys),
        field_name="resume.rejected_ambiguous_retained_count",
        context=context,
    )
    _exact(
        int(feasibility.get("rejected_retained_row_count") or -1),
        len(row_keys),
        field_name="feasibility.rejected_retained_row_count",
        context=context,
    )
    _exact(
        len(resume_keys),
        ACCEPTED_REJECTED_RECOVERED_ROWS,
        field_name="rejected_retained_rows",
        context=context,
    )
    return tuple(sorted(resume_keys))


def prove_retained_acquisition_credit(
    selected: Sequence[PhysicalObject],
    cost: Sequence[PhysicalObject],
    *,
    report: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    sample_dir: Path,
    sidecar_dir: Path,
) -> dict[str, Any]:
    """Re-prove the accepted Gate-2 retained credit over the whole requirement.

    ADR-0022 makes three quantities distinct, and this proves all three from evidence:
    valid logical requirement keys, the unique content-addressed objects behind them, and
    the bytes of those unique objects. ADR-0023 fixes the domain and the split. The domain
    is every effective checkpoint row whose full key belongs to the complete selected
    archive requirement or the complete cost requirement - never the sizing cohort, never
    an arbitrary checkpoint row, and never the selected manifest's separate consumable
    fact. A selected key earns credit on its own re-proved evidence even when its manifest
    row conservatively remains unconsumable.

    Path-bound authority is applied first: a persisted basename-only recovery binds a full
    key only when the complete frozen candidate domain resolves that basename to exactly
    that one key, and every report-declared rejected row is excluded outright. Each
    surviving key is then credited only after its object and its provider sidecar are
    rehashed and its declared byte size is proved equal to the size actually on disk; a
    checkpoint claim, report count, or basename earns nothing.

    Each surviving logical key is classified by actual membership in the selected or cost
    requirement set. Neither side is ever inferred by subtraction from the other or from
    the manifest-consumable count.

    The report's own accepted retained summary is proved field by field first, so an
    altered quantity blocks by name before any measurement or publication.
    """
    requirement = tuple(selected) + tuple(cost)
    selected_domain = {item.key for item in selected}
    cost_domain = {item.key for item in cost}
    context = {"requirement": len(requirement)}
    overlap = sorted(selected_domain & cost_domain)
    _require(
        not overlap,
        "a key belongs to both the selected and the cost requirement",
        {**context, "keys": overlap[:8]},
    )
    summary = prove_report_retained_summary(report)
    rejected = set(report_rejected_retained_keys(report))
    # The complete frozen candidate domain is every requirement key, so basename
    # ambiguity is decided against the same universe the release itself selected.
    domain = RetainedChecksumIndex().bind_candidate_domain(
        [item.key for item in requirement]
    )
    digests: set[str] = set()
    seen_keys: set[str] = set()
    keys: list[str] = []
    selected_keys: list[str] = []
    cost_keys: list[str] = []
    byte_total = 0
    unverified = 0
    for item in sorted(requirement, key=lambda row: row.key):
        entry = checkpoint.get(item.key)
        if not isinstance(entry, dict) or str(entry.get("status") or "") != "complete":
            continue
        if item.key in rejected:
            # Preserved lineage: no key, no object, no byte.
            continue
        if entry.get("recovered_from_retained_bytes") is True and not domain.binds_full_key(
            item.key
        ):
            # A basename-only recovery the frozen domain cannot bind, even if the report
            # did not list it: the rule is applied, not merely trusted.
            continue
        if item.key in cost_domain:
            # Membership in the complete cost requirement, not the family label.
            bucket = cost_keys
        elif item.key in selected_domain:
            # Membership in the complete selected requirement. The manifest's separate
            # consumable flag is deliberately not consulted here.
            bucket = selected_keys
        else:
            continue
        if item.key in seen_keys:
            # The same logical key reached twice is still exactly one logical key.
            continue
        size = verify_retained_object(
            item.key,
            entry,
            sample_dir=Path(sample_dir),
            sidecar_dir=Path(sidecar_dir),
        )
        if size is None:
            unverified += 1
            continue
        declared = entry.get("byte_size")
        _require(
            isinstance(declared, int)
            and not isinstance(declared, bool)
            and declared > 0
            and declared == size,
            "a credited retained row's declared byte size is not its actual size",
            {**context, "key": item.key, "declared": declared, "actual": size},
        )
        digest = str(entry.get("sha256") or "")
        _require(
            bool(digest),
            "a credited retained row has no content digest",
            {**context, "key": item.key},
        )
        seen_keys.add(item.key)
        keys.append(item.key)
        bucket.append(item.key)
        if digest in digests:
            # A second valid full-key binding to the same bytes: one more logical key,
            # no additional object and no additional byte.
            continue
        digests.add(digest)
        byte_total += size
    _exact(
        unverified,
        ACCEPTED_UNVERIFIED_RETAINED_OBJECTS,
        field_name="unverified_retained_objects",
        context=context,
    )
    _exact(
        len(selected_keys),
        ACCEPTED_SELECTED_RETAINED_KEYS,
        field_name="selected_retained_keys",
        context=context,
    )
    _exact(
        len(cost_keys),
        ACCEPTED_COST_RETAINED_KEYS,
        field_name="cost_retained_keys",
        context=context,
    )
    _exact(
        len(keys),
        ACCEPTED_RETAINED_CREDIT_KEYS,
        field_name="retained_credit_keys",
        context=context,
    )
    _exact(
        len(digests),
        ACCEPTED_RETAINED_CREDIT_OBJECTS,
        field_name="retained_credit_objects",
        context=context,
    )
    _exact(
        byte_total,
        ACCEPTED_RETAINED_CREDIT_BYTES,
        field_name="retained_credit_bytes",
        context=context,
    )
    return {
        "valid_requirement_keys": len(keys),
        "objects": len(digests),
        "bytes": byte_total,
        "keys": sorted(keys),
        "key_set_sha256": requirement_key_set_sha256(keys),
        "selected_retained_keys": len(selected_keys),
        "cost_retained_keys": len(cost_keys),
        "rejected_recovered_rows": len(rejected),
        "unverified_objects": unverified,
        "report_summary": dict(summary),
        "source": (
            "effective checkpoint rows inside the complete selected-plus-cost "
            "requirement, path-bound, rehashed, and deduplicated by content digest"
        ),
    }


def reconcile_physical_inputs(
    *,
    selected: Sequence[PhysicalObject],
    cost: Sequence[PhysicalObject],
    retained_credit_objects: int,
    retained_credit_bytes: int,
) -> dict[str, Any]:
    """Prove the exact accepted physical requirement before anything is projected."""
    context = {"selected": len(selected), "cost": len(cost)}
    keys = {item.key for item in selected}
    cost_keys = {item.key for item in cost}
    overlap = sorted(keys & cost_keys)
    _require(not overlap, "selected and cost objects overlap", {**context, "keys": overlap[:8]})
    combined_objects = len(selected) + len(cost)
    combined_bytes = sum(item.byte_size for item in selected) + sum(
        item.byte_size for item in cost
    )
    _exact(
        combined_objects,
        ACCEPTED_COMBINED_OBJECTS,
        field_name="combined_object_count",
        context=context,
    )
    _exact(
        combined_bytes,
        ACCEPTED_COMBINED_BYTES,
        field_name="combined_bytes",
        context=context,
    )
    _exact(
        retained_credit_objects,
        ACCEPTED_RETAINED_CREDIT_OBJECTS,
        field_name="retained_credit_objects",
        context=context,
    )
    _exact(
        retained_credit_bytes,
        ACCEPTED_RETAINED_CREDIT_BYTES,
        field_name="retained_credit_bytes",
        context=context,
    )
    projected_new = combined_bytes - retained_credit_bytes
    _exact(
        projected_new,
        ACCEPTED_NEW_BINANCE_RAW_BYTES,
        field_name="projected_new_binance_raw_bytes",
        context=context,
    )
    return {
        "selected_objects": len(selected),
        "selected_bytes": sum(item.byte_size for item in selected),
        "cost_objects": len(cost),
        "cost_bytes": sum(item.byte_size for item in cost),
        "combined_objects": combined_objects,
        "combined_bytes": combined_bytes,
        "retained_credit_objects": retained_credit_objects,
        "retained_credit_bytes": retained_credit_bytes,
        "projected_new_binance_raw_bytes": projected_new,
        "overlap_objects": 0,
        "unknown_size_objects": 0,
    }


# --- frozen cohort ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CohortSample:
    """One unique physical retained object the accepted plan selected."""

    key: str
    family: str
    symbol: str
    economic_interval: str
    action: str
    byte_size: int
    url: str
    aliases: int


def derive_sample_cohort(authority: SizingAuthority) -> tuple[CohortSample, ...]:
    """The frozen cohort, with the accepted plan's own action accounting proved.

    An alias may only name a physical key another entry already selected, and it must
    agree with that entry on family, symbol, interval, URL, and size. Anything else is
    unproved duplication and blocks.
    """
    context = {"plan_entries": len(authority.plan_entries)}
    actions: dict[str, int] = {}
    selected: dict[str, CohortSample] = {}
    alias_counts: dict[str, int] = {}
    aliases: list[Mapping[str, Any]] = []
    for entry in authority.plan_entries:
        action = str(entry.get("action") or "")
        actions[action] = actions.get(action, 0) + 1
        key = str(entry.get("key") or "")
        family = str(entry.get("family") or "")
        _require(
            family in PHYSICAL_FAMILIES,
            "a planned object is outside the 12 physical families",
            {**context, "key": key, "family": family},
        )
        size = entry.get("byte_size")
        _require(
            isinstance(size, int) and not isinstance(size, bool) and size >= 0,
            "a planned object has no integer size",
            {**context, "key": key},
        )
        sample = CohortSample(
            key=key,
            family=family,
            symbol=str(entry.get("symbol") or ""),
            economic_interval=_economic_interval(key),
            action=action,
            byte_size=int(size),
            url=str(entry.get("url") or ""),
            aliases=0,
        )
        if action == "alias":
            aliases.append({"key": key, "sample": sample})
            continue
        _require(
            key not in selected,
            "a non-alias plan entry duplicates a physical key",
            {**context, "key": key},
        )
        selected[key] = sample
    for name, expected in sorted(ACCEPTED_PLAN_ACTIONS.items()):
        _exact(
            actions.get(name, 0), expected, field_name=f"plan_action[{name}]", context=context
        )
    for item in aliases:
        key = str(item["key"])
        sample = item["sample"]
        target = selected.get(key)
        _require(
            target is not None,
            "an alias names no already selected physical key",
            {**context, "key": key},
        )
        assert target is not None
        _require(
            (target.family, target.symbol, target.economic_interval, target.url,
             target.byte_size)
            == (sample.family, sample.symbol, sample.economic_interval, sample.url,
                sample.byte_size),
            "an alias disagrees with the object it names",
            {**context, "key": key},
        )
        alias_counts[key] = alias_counts.get(key, 0) + 1
    cohort = tuple(
        CohortSample(
            key=item.key,
            family=item.family,
            symbol=item.symbol,
            economic_interval=item.economic_interval,
            action=item.action,
            byte_size=item.byte_size,
            url=item.url,
            aliases=alias_counts.get(item.key, 0),
        )
        for item in sorted(selected.values(), key=lambda row: row.key)
    )
    _exact(
        len(cohort), ACCEPTED_SAMPLE_COHORT, field_name="cohort_size", context=context
    )
    observed = {item.family for item in cohort}
    missing = [family for family in PHYSICAL_FAMILIES if family not in observed]
    _require(
        not missing,
        "the cohort does not cover every physical family",
        {**context, "missing": missing},
    )
    return cohort


# --- lossless envelope measurement -----------------------------------------------------


# --- ADR-0024 typed required-product contract -------------------------------------------

# Exact fixed decimal policy. Every price, quantity, volume, notional, rate, ratio,
# percentage, and liquidation value is carried as an exact scaled integer. Nothing on
# this path is ever converted through a binary float, and nothing is ever rounded.
DECIMAL_PRECISION: int = 38
DECIMAL_SCALE: int = 18
_DECIMAL_LEXEME = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
# A shift this large already exceeds the pinned precision, so it bounds the integer
# power computation without changing any accepted result.
_MAX_DECIMAL_SHIFT: int = DECIMAL_PRECISION + DECIMAL_SCALE + 8
_EPOCH_ORDINAL: int = date(1970, 1, 1).toordinal()

KIND_INTEGER: str = "integer"
KIND_DECIMAL: str = "exact_decimal"
KIND_DICTIONARY: str = "dictionary"
KIND_TIMESTAMP_TEXT: str = "timestamp_text_ms"
KIND_PARTITION_REF: str = "partition_local_reference"
KIND_ORDINAL: str = "source_row_ordinal"
KIND_BOOLEAN: str = "boolean"
KIND_STRING: str = "opaque_string"
KIND_STRING_LIST: str = "string_list"

_ARROW_TYPES: Mapping[str, pa.DataType] = {
    KIND_INTEGER: pa.int64(),
    KIND_DECIMAL: pa.decimal128(DECIMAL_PRECISION, DECIMAL_SCALE),
    KIND_DICTIONARY: pa.dictionary(pa.int32(), pa.string()),
    KIND_TIMESTAMP_TEXT: pa.int64(),
    KIND_PARTITION_REF: pa.int32(),
    KIND_ORDINAL: pa.int64(),
    KIND_BOOLEAN: pa.bool_(),
    # High-cardinality opaque identities and lossless accepted lists. Dictionary
    # encoding would only add an index to values that never repeat.
    KIND_STRING: pa.string(),
    KIND_STRING_LIST: pa.list_(pa.string()),
}

# The ticket's fixed required products. These names are contract, not implementation
# choices, and this module may not invent, rename, split, or merge one.
PRODUCT_MEMBERSHIP: str = "binance_usdm_perpetual_membership"
PRODUCT_BAR_1H: str = "binance_usdm_bar_1h"
PRODUCT_TRADE_FLOW_1H: str = "binance_usdm_trade_flow_1h"
PRODUCT_OPEN_INTEREST_5M: str = "binance_usdm_open_interest_5m"
PRODUCT_FUNDING_REALIZED: str = "binance_usdm_funding_realized"
PRODUCT_FUNDING_INDICATIVE_1H: str = "binance_usdm_funding_indicative_1h"
PRODUCT_MARK_INDEX_BASIS_1H: str = "binance_usdm_mark_index_basis_1h"
PRODUCT_LIQUIDATION_OBSERVED_DAILY: str = "binance_usdm_liquidation_observed_daily"
PRODUCT_COST_CALIBRATION: str = "binance_usdm_cost_calibration"
PRODUCT_COVERAGE_GAP: str = "binance_usdm_coverage_gap"
PRODUCT_BUNDLE: str = "binance_usdm_harmonic_bundle"

REQUIRED_PRODUCTS: tuple[str, ...] = (
    PRODUCT_MEMBERSHIP,
    PRODUCT_BAR_1H,
    PRODUCT_TRADE_FLOW_1H,
    PRODUCT_OPEN_INTEREST_5M,
    PRODUCT_FUNDING_REALIZED,
    PRODUCT_FUNDING_INDICATIVE_1H,
    PRODUCT_MARK_INDEX_BASIS_1H,
    PRODUCT_LIQUIDATION_OBSERVED_DAILY,
    PRODUCT_COST_CALIBRATION,
    PRODUCT_COVERAGE_GAP,
    PRODUCT_BUNDLE,
)

# Fixed source cadence per physical family. A family with no declared fixed cadence is
# named explicitly as event-driven; an unlisted family blocks rather than silently
# becoming event-driven.
FAMILY_CADENCE_SECONDS: Mapping[str, int] = {
    "daily/klines": 3_600,
    "monthly/klines": 3_600,
    "daily/metrics": 300,
    # ADR-0025 section 7: Binance has published four-hour contracts and a one-hour
    # adjustment rule, so one hour is the conservative ceiling until a stricter proved
    # complete-history lower bound exists.
    "monthly/fundingRate": 3_600,
    "daily/premiumIndexKlines": 3_600,
    "monthly/premiumIndexKlines": 3_600,
    "daily/markPriceKlines": 3_600,
    "monthly/markPriceKlines": 3_600,
    "daily/indexPriceKlines": 3_600,
    "monthly/indexPriceKlines": 3_600,
}
EVENT_DRIVEN_FAMILIES: frozenset[str] = frozenset({"daily/bookTicker", "daily/bookDepth"})


@dataclass(frozen=True, slots=True)
class TypedColumn:
    """One typed target column and the exact source token it is converted from."""

    name: str
    kind: str
    source_field: str = ""
    nullable: bool = False

    def field(self) -> pa.Field:
        return pa.field(self.name, _ARROW_TYPES[self.kind], nullable=self.nullable)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "arrow_type": str(_ARROW_TYPES[self.kind]),
            "source_field": self.source_field,
            "nullable": self.nullable,
        }


@dataclass(frozen=True, slots=True)
class ProductContribution:
    """What one physical family contributes to one required product's partitions."""

    product: str
    family: str
    component: str
    columns: tuple[TypedColumn, ...]

    @property
    def name(self) -> str:
        return f"{self.product}:{self.component}"

    def schema(self) -> pa.Schema:
        return pa.schema([column.field() for column in self.columns])

    def source_fields(self) -> tuple[str, ...]:
        return tuple(
            column.source_field for column in self.columns if column.source_field
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_product": self.product,
            "component": self.component,
            "physical_family": self.family,
            "columns": [column.to_dict() for column in self.columns],
            "source_fields": list(self.source_fields()),
        }


def _identity_columns() -> tuple[TypedColumn, ...]:
    """Compact lineage: a partition-local reference, an ordinal, and one dictionary."""
    return (
        TypedColumn("raw_object_ref", KIND_PARTITION_REF),
        TypedColumn("source_row_ordinal", KIND_ORDINAL),
        TypedColumn("venue_symbol", KIND_DICTIONARY),
    )


def _typed(name: str, kind: str, source: str, *, nullable: bool = False) -> TypedColumn:
    return TypedColumn(name, kind, source_field=source, nullable=nullable)


_OHLCV: tuple[TypedColumn, ...] = (
    _typed("open_time", KIND_INTEGER, "open_time"),
    _typed("close_time", KIND_INTEGER, "close_time"),
    _typed("open", KIND_DECIMAL, "open"),
    _typed("high", KIND_DECIMAL, "high"),
    _typed("low", KIND_DECIMAL, "low"),
    _typed("close", KIND_DECIMAL, "close"),
    _typed("volume", KIND_DECIMAL, "volume"),
    _typed("quote_volume", KIND_DECIMAL, "quote_volume"),
    _typed("trade_count", KIND_INTEGER, "count"),
    # Binance's fixed trailing column, carried typed so no declared field is dropped.
    _typed("source_reserved", KIND_INTEGER, "ignore"),
)
# Trade flow keeps the totals as well as the taker-buy side, so taker-sell volume and
# the buy/sell imbalance are derivable without returning to the raw archive.
_TRADE_FLOW: tuple[TypedColumn, ...] = (
    _typed("open_time", KIND_INTEGER, "open_time"),
    _typed("close_time", KIND_INTEGER, "close_time"),
    _typed("volume", KIND_DECIMAL, "volume"),
    _typed("quote_volume", KIND_DECIMAL, "quote_volume"),
    _typed("taker_buy_volume", KIND_DECIMAL, "taker_buy_volume"),
    _typed("taker_buy_quote_volume", KIND_DECIMAL, "taker_buy_quote_volume"),
    _typed("trade_count", KIND_INTEGER, "count"),
)
# The premium index bar contributes the indicative funding basis input.
_PREMIUM_INDICATIVE: tuple[TypedColumn, ...] = (
    _typed("open_time", KIND_INTEGER, "open_time"),
    _typed("close_time", KIND_INTEGER, "close_time"),
    _typed("premium_open", KIND_DECIMAL, "open"),
    _typed("premium_high", KIND_DECIMAL, "high"),
    _typed("premium_low", KIND_DECIMAL, "low"),
    _typed("premium_close", KIND_DECIMAL, "close"),
    _typed("premium_volume", KIND_DECIMAL, "volume"),
    _typed("premium_quote_volume", KIND_DECIMAL, "quote_volume"),
    _typed("premium_count", KIND_INTEGER, "count"),
    _typed("premium_taker_buy_volume", KIND_DECIMAL, "taker_buy_volume"),
    _typed(
        "premium_taker_buy_quote_volume", KIND_DECIMAL, "taker_buy_quote_volume"
    ),
    _typed("source_reserved", KIND_INTEGER, "ignore"),
)
# The same premium index bar also contributes the basis component of mark/index basis.
_PREMIUM_BASIS: tuple[TypedColumn, ...] = (
    _typed("open_time", KIND_INTEGER, "open_time"),
    _typed("close_time", KIND_INTEGER, "close_time"),
    _typed("premium_close", KIND_DECIMAL, "close"),
)
_MARK_PRICE: tuple[TypedColumn, ...] = (
    _typed("open_time", KIND_INTEGER, "open_time"),
    _typed("close_time", KIND_INTEGER, "close_time"),
    _typed("mark_open", KIND_DECIMAL, "open"),
    _typed("mark_high", KIND_DECIMAL, "high"),
    _typed("mark_low", KIND_DECIMAL, "low"),
    _typed("mark_close", KIND_DECIMAL, "close"),
    _typed("mark_volume", KIND_DECIMAL, "volume"),
    _typed("mark_quote_volume", KIND_DECIMAL, "quote_volume"),
    _typed("mark_count", KIND_INTEGER, "count"),
    _typed("mark_taker_buy_volume", KIND_DECIMAL, "taker_buy_volume"),
    _typed("mark_taker_buy_quote_volume", KIND_DECIMAL, "taker_buy_quote_volume"),
    _typed("source_reserved", KIND_INTEGER, "ignore"),
)
_INDEX_PRICE: tuple[TypedColumn, ...] = (
    _typed("open_time", KIND_INTEGER, "open_time"),
    _typed("close_time", KIND_INTEGER, "close_time"),
    _typed("index_open", KIND_DECIMAL, "open"),
    _typed("index_high", KIND_DECIMAL, "high"),
    _typed("index_low", KIND_DECIMAL, "low"),
    _typed("index_close", KIND_DECIMAL, "close"),
    _typed("index_volume", KIND_DECIMAL, "volume"),
    _typed("index_quote_volume", KIND_DECIMAL, "quote_volume"),
    _typed("index_count", KIND_INTEGER, "count"),
    _typed("index_taker_buy_volume", KIND_DECIMAL, "taker_buy_volume"),
    _typed("index_taker_buy_quote_volume", KIND_DECIMAL, "taker_buy_quote_volume"),
    _typed("source_reserved", KIND_INTEGER, "ignore"),
)
_OPEN_INTEREST: tuple[TypedColumn, ...] = (
    _typed("create_time", KIND_TIMESTAMP_TEXT, "create_time"),
    _typed("metric_symbol", KIND_DICTIONARY, "symbol"),
    _typed("sum_open_interest", KIND_DECIMAL, "sum_open_interest"),
    _typed("sum_open_interest_value", KIND_DECIMAL, "sum_open_interest_value"),
    _typed(
        "count_toptrader_long_short_ratio",
        KIND_DECIMAL,
        "count_toptrader_long_short_ratio",
        nullable=True,
    ),
    _typed(
        "sum_toptrader_long_short_ratio",
        KIND_DECIMAL,
        "sum_toptrader_long_short_ratio",
        nullable=True,
    ),
    _typed(
        "count_long_short_ratio",
        KIND_DECIMAL,
        "count_long_short_ratio",
        nullable=True,
    ),
    _typed(
        "sum_taker_long_short_vol_ratio",
        KIND_DECIMAL,
        "sum_taker_long_short_vol_ratio",
        nullable=True,
    ),
)
_FUNDING_REALIZED: tuple[TypedColumn, ...] = (
    _typed("calc_time", KIND_INTEGER, "calc_time"),
    _typed("funding_interval_hours", KIND_INTEGER, "funding_interval_hours"),
    _typed("last_funding_rate", KIND_DECIMAL, "last_funding_rate"),
)
# The cost product keeps every valid field of every selected row. ADR-0024 forbids any
# cost-row, cost-field, or cost-sample reduction.
_BOOK_TICKER: tuple[TypedColumn, ...] = (
    _typed("update_id", KIND_INTEGER, "update_id"),
    _typed("best_bid_price", KIND_DECIMAL, "best_bid_price"),
    _typed("best_bid_qty", KIND_DECIMAL, "best_bid_qty"),
    _typed("best_ask_price", KIND_DECIMAL, "best_ask_price"),
    _typed("best_ask_qty", KIND_DECIMAL, "best_ask_qty"),
    _typed("transaction_time", KIND_INTEGER, "transaction_time"),
    _typed("event_time", KIND_INTEGER, "event_time"),
)
_BOOK_DEPTH: tuple[TypedColumn, ...] = (
    _typed("timestamp", KIND_TIMESTAMP_TEXT, "timestamp"),
    _typed("percentage", KIND_DECIMAL, "percentage"),
    _typed("depth", KIND_DECIMAL, "depth"),
    _typed("notional", KIND_DECIMAL, "notional"),
)

_CONTRIBUTIONS: tuple[tuple[str, str, str, tuple[TypedColumn, ...]], ...] = (
    (PRODUCT_BAR_1H, "daily/klines", "daily_klines", _OHLCV),
    (PRODUCT_BAR_1H, "monthly/klines", "monthly_klines", _OHLCV),
    (PRODUCT_TRADE_FLOW_1H, "daily/klines", "daily_klines", _TRADE_FLOW),
    (PRODUCT_TRADE_FLOW_1H, "monthly/klines", "monthly_klines", _TRADE_FLOW),
    (PRODUCT_OPEN_INTEREST_5M, "daily/metrics", "daily_metrics", _OPEN_INTEREST),
    (
        PRODUCT_FUNDING_REALIZED,
        "monthly/fundingRate",
        "monthly_funding_rate",
        _FUNDING_REALIZED,
    ),
    (
        PRODUCT_FUNDING_INDICATIVE_1H,
        "daily/premiumIndexKlines",
        "daily_premium_index",
        _PREMIUM_INDICATIVE,
    ),
    (
        PRODUCT_FUNDING_INDICATIVE_1H,
        "monthly/premiumIndexKlines",
        "monthly_premium_index",
        _PREMIUM_INDICATIVE,
    ),
    (
        PRODUCT_MARK_INDEX_BASIS_1H,
        "daily/markPriceKlines",
        "daily_mark_price",
        _MARK_PRICE,
    ),
    (
        PRODUCT_MARK_INDEX_BASIS_1H,
        "monthly/markPriceKlines",
        "monthly_mark_price",
        _MARK_PRICE,
    ),
    (
        PRODUCT_MARK_INDEX_BASIS_1H,
        "daily/indexPriceKlines",
        "daily_index_price",
        _INDEX_PRICE,
    ),
    (
        PRODUCT_MARK_INDEX_BASIS_1H,
        "monthly/indexPriceKlines",
        "monthly_index_price",
        _INDEX_PRICE,
    ),
    (
        PRODUCT_MARK_INDEX_BASIS_1H,
        "daily/premiumIndexKlines",
        "daily_premium_basis",
        _PREMIUM_BASIS,
    ),
    (
        PRODUCT_MARK_INDEX_BASIS_1H,
        "monthly/premiumIndexKlines",
        "monthly_premium_basis",
        _PREMIUM_BASIS,
    ),
    (
        PRODUCT_COST_CALIBRATION,
        "daily/bookTicker",
        "daily_book_ticker",
        _BOOK_TICKER,
    ),
    (
        PRODUCT_COST_CALIBRATION,
        "daily/bookDepth",
        "daily_book_depth",
        _BOOK_DEPTH,
    ),
)

PRODUCT_CONTRIBUTIONS: tuple[ProductContribution, ...] = tuple(
    ProductContribution(
        product=product,
        family=family,
        component=component,
        columns=_identity_columns() + columns,
    )
    for product, family, component, columns in _CONTRIBUTIONS
)

# --- products that are not fed by a physical archive family ---------------------------

ARCHIVE_PARTITION_MANIFEST_SCHEMA: pa.Schema = pa.schema(
    [
        pa.field("raw_object_ref", pa.int32(), nullable=False),
        pa.field("required_product", pa.dictionary(pa.int32(), pa.string()), nullable=False),
        pa.field("component", pa.dictionary(pa.int32(), pa.string()), nullable=False),
        pa.field("native_symbol", pa.dictionary(pa.int32(), pa.string()), nullable=False),
        pa.field("utc_month", pa.dictionary(pa.int32(), pa.string()), nullable=False),
        pa.field("source_key", pa.string(), nullable=False),
        pa.field("source_state", pa.dictionary(pa.int32(), pa.string()), nullable=False),
        pa.field("source_sha256", pa.string(), nullable=True),
        pa.field("checksum_authority", pa.string(), nullable=True),
        pa.field("retrieval_time", pa.string(), nullable=True),
        pa.field("availability_semantics", pa.dictionary(pa.int32(), pa.string()), nullable=False),
        pa.field("source_available_at", pa.int64(), nullable=True),
        pa.field("requirement_byte_size", pa.int64(), nullable=False),
    ]
)
COINALYZE_PARTITION_MANIFEST_SCHEMA: pa.Schema = pa.schema(
    [
        field
        for field in ARCHIVE_PARTITION_MANIFEST_SCHEMA
        if field.name != "requirement_byte_size"
    ]
    + [
        pa.field("provider_symbol", pa.dictionary(pa.int32(), pa.string()), nullable=False),
        pa.field("projected_response_bytes", pa.int64(), nullable=True),
        pa.field("projected_response_rows", pa.int64(), nullable=True),
    ]
)
# Backward-compatible public name for the archive contract. The receipt publishes both.
PARTITION_MANIFEST_SCHEMA: pa.Schema = ARCHIVE_PARTITION_MANIFEST_SCHEMA

# The four required products no physical archive family feeds. Their complete target
# schemas are declared below with every other product's.
NON_ARCHIVE_PRODUCTS: tuple[str, ...] = (
    PRODUCT_MEMBERSHIP,
    PRODUCT_COVERAGE_GAP,
    PRODUCT_LIQUIDATION_OBSERVED_DAILY,
    PRODUCT_BUNDLE,
)


# --- ADR-0025 section 2: the complete final target schemas --------------------------

# Native identity is real and available now. The REF-001 canonical instrument and
# version identities do not exist yet: no Gate-1 artifact has created those reference
# rows, so they are declared as nullable future Gate-3 fields whose exact encoded widths
# are allocated separately and explicitly, never filled with a ticker-derived string.
_NATIVE_IDENTITY: tuple[TypedColumn, ...] = (
    TypedColumn("venue", KIND_DICTIONARY),
    TypedColumn("native_symbol", KIND_DICTIONARY),
)
_FUTURE_REFERENCE_IDENTITY: tuple[TypedColumn, ...] = (
    TypedColumn("canonical_instrument_id", KIND_DICTIONARY, nullable=True),
    TypedColumn("canonical_instrument_version_id", KIND_DICTIONARY, nullable=True),
    TypedColumn("reference_identity_state", KIND_DICTIONARY),
)
_INSTRUMENT_IDENTITY: tuple[TypedColumn, ...] = (
    _NATIVE_IDENTITY + _FUTURE_REFERENCE_IDENTITY
)
FUTURE_REFERENCE_FIELD_WIDTHS: Mapping[str, int] = {
    "canonical_instrument_id": REF_INSTRUMENT_ID_WIDTH,
    "canonical_instrument_version_id": REF_INSTRUMENT_VERSION_ID_WIDTH,
}

# Target-only columns: fields the normalizer must publish that no physical contribution
# already allocates. Each is allocated exactly once, in exactly one product.
DERIVED_COLUMNS: Mapping[str, tuple[TypedColumn, ...]] = {
    PRODUCT_BAR_1H: _INSTRUMENT_IDENTITY,
    PRODUCT_TRADE_FLOW_1H: _INSTRUMENT_IDENTITY
    + (
        TypedColumn("taker_sell_volume", KIND_DECIMAL),
        TypedColumn("taker_sell_quote_volume", KIND_DECIMAL),
        TypedColumn("volume_imbalance", KIND_DECIMAL),
        TypedColumn("quote_volume_imbalance", KIND_DECIMAL),
    ),
    PRODUCT_OPEN_INTEREST_5M: _INSTRUMENT_IDENTITY
    + (
        TypedColumn("previous_sum_open_interest", KIND_DECIMAL, nullable=True),
        TypedColumn("open_interest_change", KIND_DECIMAL, nullable=True),
        TypedColumn("open_interest_value_change", KIND_DECIMAL, nullable=True),
        TypedColumn("change_interval_seconds", KIND_INTEGER, nullable=True),
        TypedColumn("gap_break_status", KIND_DICTIONARY),
    ),
    PRODUCT_FUNDING_REALIZED: _INSTRUMENT_IDENTITY
    + (
        TypedColumn("long_cashflow_rate", KIND_DECIMAL),
        TypedColumn("short_cashflow_rate", KIND_DECIMAL),
        TypedColumn("cashflow_sign_convention", KIND_DICTIONARY),
    ),
    PRODUCT_FUNDING_INDICATIVE_1H: _INSTRUMENT_IDENTITY
    + (
        # No retained source publishes a direct indicative rate, so it is typed nullable
        # and gapped rather than fabricated from the premium inputs.
        TypedColumn("indicative_funding_rate", KIND_DECIMAL, nullable=True),
        TypedColumn("indicative_rate_status", KIND_DICTIONARY),
    ),
    PRODUCT_MARK_INDEX_BASIS_1H: _INSTRUMENT_IDENTITY
    + (
        TypedColumn("absolute_basis", KIND_DECIMAL),
        TypedColumn("relative_basis", KIND_DECIMAL),
        TypedColumn("basis_join_status", KIND_DICTIONARY),
    ),
}

MEMBERSHIP_SCHEMA_COLUMNS: tuple[TypedColumn, ...] = _INSTRUMENT_IDENTITY + (
    TypedColumn("membership_class", KIND_DICTIONARY),
    TypedColumn("contract_type", KIND_DICTIONARY),
    TypedColumn("contract_metadata_state", KIND_DICTIONARY),
    TypedColumn("contract_evidence_class", KIND_DICTIONARY),
    TypedColumn("contract_evidence_source", KIND_STRING),
    TypedColumn("contract_status", KIND_DICTIONARY, nullable=True),
    TypedColumn("underlying_type", KIND_DICTIONARY, nullable=True),
    TypedColumn("base_asset", KIND_DICTIONARY, nullable=True),
    TypedColumn("quote_asset", KIND_DICTIONARY, nullable=True),
    TypedColumn("margin_asset", KIND_DICTIONARY, nullable=True),
    TypedColumn("pair", KIND_DICTIONARY, nullable=True),
    TypedColumn("in_archive", KIND_BOOLEAN),
    TypedColumn("in_current_exchange", KIND_BOOLEAN),
    TypedColumn("onboard_ms", KIND_INTEGER, nullable=True),
    TypedColumn("delivery_ms", KIND_INTEGER, nullable=True),
    TypedColumn("closed_observed_ms", KIND_INTEGER, nullable=True),
    TypedColumn("semantics_state", KIND_DICTIONARY),
    TypedColumn("contract_snapshot_sha256", KIND_STRING, nullable=True),
    TypedColumn("evidence_records", KIND_INTEGER),
)
# Every accepted source-gap field survives, including the complete family list and the
# observed bounds as observed bounds.
COVERAGE_GAP_COLUMNS: tuple[TypedColumn, ...] = _INSTRUMENT_IDENTITY + (
    TypedColumn("required_product", KIND_DICTIONARY),
    TypedColumn("family_group", KIND_DICTIONARY),
    TypedColumn("families", KIND_STRING_LIST),
    TypedColumn("family_count", KIND_INTEGER),
    TypedColumn("gap_kind", KIND_DICTIONARY),
    TypedColumn("gap_status", KIND_DICTIONARY),
    TypedColumn("blocking", KIND_BOOLEAN),
    TypedColumn("observed_months", KIND_INTEGER, nullable=True),
    TypedColumn("first_observed_period", KIND_DICTIONARY),
    TypedColumn("last_observed_period", KIND_DICTIONARY),
    TypedColumn("family_first_observed_period", KIND_DICTIONARY),
    TypedColumn("family_last_observed_period", KIND_DICTIONARY),
    TypedColumn("onboard_period", KIND_DICTIONARY),
    TypedColumn("close_period", KIND_DICTIONARY),
    TypedColumn("missing_months", KIND_STRING_LIST),
    TypedColumn("missing_month_count", KIND_INTEGER, nullable=True),
    TypedColumn("objects", KIND_INTEGER, nullable=True),
    TypedColumn("explained_by", KIND_DICTIONARY),
)
TYPED_GAP_MEMBERSHIP_COLUMNS: tuple[TypedColumn, ...] = _INSTRUMENT_IDENTITY + (
    TypedColumn("required_product", KIND_DICTIONARY),
)
QUALITY_GAP_COLUMNS: tuple[TypedColumn, ...] = _INSTRUMENT_IDENTITY + (
    TypedColumn("required_product", KIND_DICTIONARY),
    TypedColumn("utc_month", KIND_DICTIONARY),
    TypedColumn("missing_run_start_ms", KIND_INTEGER, nullable=True),
    TypedColumn("missing_run_end_ms", KIND_INTEGER, nullable=True),
    TypedColumn("expected_grid_count", KIND_INTEGER),
    TypedColumn("gap_kind", KIND_DICTIONARY),
    TypedColumn("reason", KIND_DICTIONARY),
)
FEE_AUTHORITY_GAP_COLUMNS: tuple[TypedColumn, ...] = _INSTRUMENT_IDENTITY + (
    TypedColumn("required_product", KIND_DICTIONARY),
    TypedColumn("gap_kind", KIND_DICTIONARY),
    TypedColumn("gap_status", KIND_DICTIONARY),
    TypedColumn("blocking", KIND_BOOLEAN),
    TypedColumn("authority_class", KIND_DICTIONARY),
    TypedColumn("explained_by", KIND_DICTIONARY),
)
# The official effective fee-schedule component. Its schema is pinned even though this
# release proves zero rows; absence never becomes zero cost.
OFFICIAL_FEE_SCHEDULE_COLUMNS: tuple[TypedColumn, ...] = _INSTRUMENT_IDENTITY + (
    TypedColumn("fee_tier", KIND_DICTIONARY),
    TypedColumn("maker_rate", KIND_DECIMAL),
    TypedColumn("taker_rate", KIND_DECIMAL),
    TypedColumn("valid_from_ms", KIND_INTEGER),
    TypedColumn("valid_to_ms", KIND_INTEGER, nullable=True),
    TypedColumn("available_from_ms", KIND_INTEGER),
    TypedColumn("available_to_ms", KIND_INTEGER, nullable=True),
    TypedColumn("authority_class", KIND_DICTIONARY),
    TypedColumn("evidence_sha256", KIND_STRING),
    TypedColumn("source_endpoint", KIND_DICTIONARY),
    TypedColumn("source_retrieval_time", KIND_STRING, nullable=True),
)
LIQUIDATION_COLUMNS: tuple[TypedColumn, ...] = _INSTRUMENT_IDENTITY + (
    TypedColumn("raw_object_ref", KIND_PARTITION_REF),
    TypedColumn("point_ordinal", KIND_ORDINAL),
    TypedColumn("provider_symbol", KIND_DICTIONARY),
    TypedColumn("event_time_ms", KIND_INTEGER),
    TypedColumn("long_liquidation", KIND_DECIMAL),
    TypedColumn("short_liquidation", KIND_DECIMAL),
    TypedColumn("liquidation_imbalance", KIND_DECIMAL),
    TypedColumn("source_interval_seconds", KIND_INTEGER),
    TypedColumn("observation_semantics", KIND_DICTIONARY),
    TypedColumn("event_complete", KIND_BOOLEAN),
)
FEE_SCENARIO_COLUMNS: tuple[TypedColumn, ...] = (
    TypedColumn("scenario_id", KIND_DICTIONARY),
    TypedColumn("role", KIND_DICTIONARY),
    TypedColumn("scope", KIND_DICTIONARY),
    TypedColumn("authority_class", KIND_DICTIONARY),
    TypedColumn("policy_known_at", KIND_DICTIONARY),
    TypedColumn("maker_rate", KIND_DECIMAL),
    TypedColumn("taker_rate", KIND_DECIMAL),
    TypedColumn("charges_each_side", KIND_BOOLEAN),
    TypedColumn("maker_credit_enabled", KIND_BOOLEAN),
    TypedColumn("rebates_enabled", KIND_BOOLEAN),
    TypedColumn("vip_discounts_enabled", KIND_BOOLEAN),
    TypedColumn("referral_discounts_enabled", KIND_BOOLEAN),
    TypedColumn("bnb_discount_enabled", KIND_BOOLEAN),
    TypedColumn("source_basis", KIND_STRING),
)
# ADR-0026: five heterogeneous components, each with its own schema and allocation.
COST_COMPONENTS: tuple[str, ...] = (
    "retained_book_ticker",
    "retained_book_depth",
    "official_fee_schedule",
    "fee_authority_gap",
    "scenario_policy",
)


def cost_component_columns(component: str) -> tuple[TypedColumn, ...]:
    """One cost component's own schema. The five are heterogeneous, never one row."""
    if component == "retained_book_ticker":
        return tuple(
            contribution(f"{PRODUCT_COST_CALIBRATION}:daily_book_ticker").columns
        ) + _INSTRUMENT_IDENTITY
    if component == "retained_book_depth":
        return tuple(
            contribution(f"{PRODUCT_COST_CALIBRATION}:daily_book_depth").columns
        ) + _INSTRUMENT_IDENTITY
    if component == "official_fee_schedule":
        return OFFICIAL_FEE_SCHEDULE_COLUMNS
    if component == "fee_authority_gap":
        return FEE_AUTHORITY_GAP_COLUMNS
    if component == "scenario_policy":
        return FEE_SCENARIO_COLUMNS
    raise SizingError("unknown cost component", context={"component": component})
BUNDLE_COLUMNS: tuple[TypedColumn, ...] = (
    TypedColumn("required_product", KIND_DICTIONARY),
    TypedColumn("component", KIND_DICTIONARY),
    TypedColumn("dataset_id", KIND_DICTIONARY),
    TypedColumn("native_symbol", KIND_DICTIONARY),
    TypedColumn("canonical_instrument_id", KIND_DICTIONARY, nullable=True),
    TypedColumn("canonical_instrument_version_id", KIND_DICTIONARY, nullable=True),
    TypedColumn("reference_identity_state", KIND_DICTIONARY),
    TypedColumn("utc_month", KIND_DICTIONARY),
    TypedColumn("partition_sha256", KIND_STRING, nullable=True),
    TypedColumn("partition_bytes", KIND_INTEGER, nullable=True),
    TypedColumn("row_count", KIND_INTEGER, nullable=True),
    TypedColumn("schema_sha256", KIND_STRING),
    TypedColumn("lineage_manifest_sha256", KIND_STRING, nullable=True),
    TypedColumn("lineage_mapping_count", KIND_INTEGER),
    TypedColumn("source_report_sha256", KIND_STRING),
    TypedColumn("source_manifest_detail_sha256", KIND_STRING),
    TypedColumn("qualification_code_sha256", KIND_STRING),
    TypedColumn("qualification_cli_sha256", KIND_STRING),
    TypedColumn("sizing_code_sha256", KIND_STRING),
    TypedColumn("sizing_cli_sha256", KIND_STRING),
    TypedColumn("configuration_sha256", KIND_STRING),
    TypedColumn("scenario_policy_sha256", KIND_STRING),
    TypedColumn("unit_convention", KIND_DICTIONARY),
    TypedColumn("censorship_semantics", KIND_DICTIONARY),
    TypedColumn("coverage_gap_rows", KIND_INTEGER),
    TypedColumn("typed_gap_membership_rows", KIND_INTEGER),
    TypedColumn("fee_authority_gap_rows", KIND_INTEGER),
    TypedColumn("cross_product_intersection_count", KIND_INTEGER),
    TypedColumn("cross_product_intersection_sha256", KIND_STRING),
)

FINAL_PRODUCT_COLUMNS: Mapping[str, tuple[TypedColumn, ...]] = {
    PRODUCT_MEMBERSHIP: MEMBERSHIP_SCHEMA_COLUMNS,
    PRODUCT_COVERAGE_GAP: COVERAGE_GAP_COLUMNS,
    PRODUCT_LIQUIDATION_OBSERVED_DAILY: LIQUIDATION_COLUMNS,
    PRODUCT_BUNDLE: BUNDLE_COLUMNS,
}


def _schema_of(columns: Sequence[TypedColumn]) -> pa.Schema:
    return pa.schema([column.field() for column in columns])


def final_product_columns(product: str) -> tuple[TypedColumn, ...]:
    """The complete target schema of one required product, in declared order."""
    if product == PRODUCT_COST_CALIBRATION:
        raise SizingError(
            "cost calibration is a five-component descriptor, not a flattened row schema",
            context={"required_product": product},
        )
    if product in FINAL_PRODUCT_COLUMNS:
        return FINAL_PRODUCT_COLUMNS[product]
    columns: list[TypedColumn] = list(_identity_columns())
    seen = {column.name for column in columns}
    for item in contributions_for_product(product):
        for column in item.columns:
            if column.name not in seen:
                columns.append(column)
                seen.add(column.name)
    for column in DERIVED_COLUMNS.get(product, ()):  # target-only fields
        _require(
            column.name not in seen,
            "a target-only field is already allocated by a contribution",
            {"required_product": product, "column": column.name},
        )
        columns.append(column)
        seen.add(column.name)
    _require(bool(columns), "a required product has no final schema", {"product": product})
    return tuple(columns)


def final_product_schema(product: str) -> pa.Schema:
    return _schema_of(final_product_columns(product))


def target_only_columns(product: str) -> tuple[TypedColumn, ...]:
    """Fields the final schema publishes that no physical contribution allocates."""
    if product == PRODUCT_COST_CALIBRATION:
        return ()
    contributed = {
        column.name
        for item in contributions_for_product(product)
        for column in item.columns
    }
    return tuple(
        column
        for column in final_product_columns(product)
        if column.name not in contributed
    )


def contributions_for_family(family: str) -> tuple[ProductContribution, ...]:
    """Every required product one physical family feeds, in declared order."""
    items = tuple(item for item in PRODUCT_CONTRIBUTIONS if item.family == family)
    _require(
        bool(items),
        "no declared required-product contribution for physical family",
        {"family": family},
    )
    return items


def contributions_for_product(product: str) -> tuple[ProductContribution, ...]:
    return tuple(item for item in PRODUCT_CONTRIBUTIONS if item.product == product)


def contribution(name: str) -> ProductContribution:
    for item in PRODUCT_CONTRIBUTIONS:
        if item.name == name:
            return item
    raise SizingError("unknown product contribution", context={"contribution": name})


def _schema_dict(schema: pa.Schema) -> list[dict[str, Any]]:
    return [
        {"name": field.name, "arrow_type": str(field.type), "nullable": field.nullable}
        for field in schema
    ]


def product_schema_contract(product: str) -> Any:
    """One final schema, or the cost descriptor's five independently typed schemas."""
    if product == PRODUCT_COST_CALIBRATION:
        return {
            component: _schema_dict(_schema_of(cost_component_columns(component)))
            for component in COST_COMPONENTS
        }
    return _schema_dict(final_product_schema(product))


def product_schema_identity(product: str) -> str:
    return _sha256_bytes(
        canonical_json({"required_product": product, "schema": product_schema_contract(product)})
    )


def partition_schema_identity(product: str, component: str) -> str:
    if product == PRODUCT_COST_CALIBRATION and component in COST_COMPONENTS:
        schema: Any = _schema_dict(_schema_of(cost_component_columns(component)))
    else:
        schema = product_schema_contract(product)
    return _sha256_bytes(
        canonical_json(
            {"required_product": product, "component": component, "schema": schema}
        )
    )


def cross_product_partition_intersection(
    partitions: Mapping[tuple[str, str, str, str], Sequence[Mapping[str, Any]]]
) -> tuple[tuple[str, str], ...]:
    """The actual native/month keys common to every projected product component."""
    by_component: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for product, component, symbol, month in partitions:
        by_component.setdefault((product, component), set()).add((symbol, month))
    _require(bool(by_component), "the projected partition intersection has no component", {})
    common = set.intersection(*by_component.values())
    return tuple(sorted(common))


def prove_product_contract() -> dict[str, Any]:
    """Prove the fixed required-product schema contract before anything is measured.

    The ticket's product names are contract. Every declared source field of every
    physical family must reach at least one typed target column, the number of products
    a family feeds must equal ADR-0021's frozen fan-out, daily and monthly packaging of
    one product must share that one product, and every family must declare either a
    fixed cadence or explicit event-driven status.
    """
    context = {"products": len(REQUIRED_PRODUCTS)}
    names = [item.name for item in PRODUCT_CONTRIBUTIONS]
    _require(
        len(set(names)) == len(names),
        "two product contributions share one name",
        context,
    )
    for item in PRODUCT_CONTRIBUTIONS:
        _require(
            item.product in REQUIRED_PRODUCTS,
            "a contribution names a product outside the ticket contract",
            {**context, "contribution": item.name},
        )
    for family in PHYSICAL_FAMILIES:
        items = contributions_for_family(family)
        products = {item.product for item in items}
        _exact(
            len(products),
            OUTPUT_MULTIPLICITY[family],
            field_name="required_products_per_family",
            context={**context, "family": family},
        )
        _require(
            family in FAMILY_CADENCE_SECONDS or family in EVENT_DRIVEN_FAMILIES,
            "a physical family declares no fixed cadence and no event-driven status",
            {**context, "family": family},
        )
        hint = family.partition("/")[2]
        declared = tuple(KNOWN_ARCHIVE_SCHEMAS.get(hint, {}).get("headerless", ()))
        _require(
            bool(declared),
            "no declared schema for physical family",
            {**context, "family": family},
        )
        covered: set[str] = set()
        for item in items:
            column_names = [column.name for column in item.columns]
            _require(
                len(set(column_names)) == len(column_names),
                "a product contribution repeats a column name",
                {**context, "contribution": item.name},
            )
            for column in item.columns:
                _require(
                    column.kind in _ARROW_TYPES,
                    "a typed column has no declared type",
                    {**context, "contribution": item.name, "column": column.name},
                )
                if column.source_field:
                    _require(
                        column.source_field in declared,
                        "a typed column names a field the family does not declare",
                        {**context, "contribution": item.name, "column": column.name},
                    )
                    covered.add(column.source_field)
        missing = sorted(set(declared) - covered)
        _require(
            not missing,
            "a declared source field reaches no typed target column",
            {**context, "family": family, "fields": missing[:8]},
        )
    # Daily and monthly packaging of one product is one product, never two.
    for product in REQUIRED_PRODUCTS:
        items = contributions_for_product(product)
        cadences = {item.family.partition("/")[0] for item in items}
        if len(items) > 1:
            _require(
                len({item.product for item in items}) == 1,
                "a product's contributions disagree about their product",
                {**context, "product": product},
            )
        _require(
            cadences <= {"daily", "monthly"},
            "a contribution names an unknown archive cadence",
            {**context, "product": product},
        )
    # Trade flow must retain the totals as well as the taker-buy side.
    flow = {
        column.source_field
        for item in contributions_for_product(PRODUCT_TRADE_FLOW_1H)
        for column in item.columns
    }
    for required in ("volume", "quote_volume", "taker_buy_volume", "taker_buy_quote_volume"):
        _require(
            required in flow,
            "trade flow does not retain the inputs needed for sell side and imbalance",
            {**context, "field": required},
        )
    # Every required product is represented by an archive contribution, a fixed schema,
    # or the cost descriptor's five independent component schemas.
    for product in REQUIRED_PRODUCTS:
        _require(
            bool(contributions_for_product(product))
            or product in NON_ARCHIVE_PRODUCTS,
            "a required product has no typed representation",
            {**context, "product": product},
        )
    return {
        "required_products": list(REQUIRED_PRODUCTS),
        "contributions": [item.to_dict() for item in PRODUCT_CONTRIBUTIONS],
        "non_archive_product_schemas": {
            product: _schema_dict(schema)
            for product, schema in (
                (name, final_product_schema(name)) for name in NON_ARCHIVE_PRODUCTS
            )
        },
        "cost_component_schemas": product_schema_contract(PRODUCT_COST_CALIBRATION),
        "partition_manifest_schemas": {
            "archive": _schema_dict(ARCHIVE_PARTITION_MANIFEST_SCHEMA),
            "coinalyze": _schema_dict(COINALYZE_PARTITION_MANIFEST_SCHEMA),
        },
        "decimal_policy": {
            "arrow_type": str(_ARROW_TYPES[KIND_DECIMAL]),
            "precision": DECIMAL_PRECISION,
            "scale": DECIMAL_SCALE,
            "rule": (
                "parsed from the original token as an exact scaled integer; a lexeme "
                "that is not exactly representable at this precision and scale blocks "
                "and is never rounded, and no value passes through a binary float"
            ),
        },
        "cadence": {
            "fixed_seconds": dict(FAMILY_CADENCE_SECONDS),
            "event_driven_families": sorted(EVENT_DRIVEN_FAMILIES),
            "rule": "an undeclared cadence blocks; it never becomes event-driven",
        },
        "packaging": (
            "daily and monthly archive packaging of one required product feeds one "
            "product partition set; packaging is a component, never a product"
        ),
    }


def safe_zip_member(payload: bytes, *, key: str) -> zipfile.ZipInfo:
    """Exactly one safe, named CSV member. Anything else is refused, never extracted."""
    context = {"key": key}
    _require(payload[:2] == b"PK", "the retained sample is not a ZIP archive", context)
    try:
        handle = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise SizingError("the retained sample ZIP is unreadable", context=context) from exc
    members = [info for info in handle.infolist() if not info.is_dir()]
    _require(len(members) == 1, "the retained sample does not hold one member", context)
    member = members[0]
    name = member.filename
    _require(bool(name), "the retained sample member has no name", context)
    _require(
        not name.startswith("/") and not name.startswith("\\"),
        "the retained sample member is an absolute path",
        {**context, "member": name},
    )
    _require(
        ".." not in Path(name.replace("\\", "/")).parts,
        "the retained sample member escapes its archive",
        {**context, "member": name},
    )
    _require(
        name.lower().endswith(".csv"),
        "the retained sample member is not a CSV file",
        {**context, "member": name},
    )
    _require(member.file_size > 0, "the retained sample member is empty", context)
    return member


def _parquet_footer_bytes(path: Path) -> tuple[int, int]:
    """The actual Parquet footer length, and the separately defined file overhead.

    The footer is the serialized file metadata whose length the trailer records. File
    overhead is the fixed magic and trailer framing around it, declared separately so
    neither is confused with the other or with an Arrow encoding difference.
    """
    with path.open("rb") as handle:
        size = path.stat().st_size
        _require(
            size > PARQUET_TRAILER_BYTES + PARQUET_MAGIC_BYTES,
            "parquet file is truncated",
            {"path": str(path)},
        )
        handle.seek(-PARQUET_TRAILER_BYTES, os.SEEK_END)
        trailer = handle.read(PARQUET_TRAILER_BYTES)
    _require(trailer[4:] == b"PAR1", "parquet trailer is not PAR1", {"path": str(path)})
    metadata_length = int(struct.unpack("<I", trailer[:4])[0])
    overhead = PARQUET_MAGIC_BYTES + PARQUET_TRAILER_BYTES
    return metadata_length, overhead


def _iter_source_rows(
    payload: bytes, *, key: str, family: str, schema_kind: str
) -> Iterator[list[str]]:
    """Stream every parsed row. The whole extracted member is never materialised."""
    member = safe_zip_member(payload, key=key)
    hint = family.partition("/")[2]
    declared = KNOWN_ARCHIVE_SCHEMAS.get(hint, {}).get("headerless", ())
    width = len(declared)
    with zipfile.ZipFile(io.BytesIO(payload)) as handle, handle.open(member) as raw:
        stream = io.TextIOWrapper(raw, encoding="utf-8", newline="")
        try:
            reader = enumerate(csv.reader(stream, strict=True))
            for index, row in reader:
                if not row:
                    continue
                header = [str(cell).strip() for cell in row] == list(declared)
                if index == 0:
                    _require(
                        header == (schema_kind == "headed"),
                        "the retained sample header form disagrees with its checkpoint",
                        {"key": key, "schema_kind": schema_kind, "header_row": header},
                    )
                    if header:
                        continue
                _require(
                    len(row) == width,
                    "a source row does not match its declared schema width",
                    {"key": key, "row": index, "width": len(row), "expected_width": width},
                )
                yield [str(cell) for cell in row]
        except (csv.Error, UnicodeDecodeError) as exc:
            raise SizingError(
                "the retained sample member is not decodable CSV", context={"key": key}
            ) from exc


def _fail(message: str, *, key: str, output: str, column: str, row: int) -> None:
    """Fail closed naming only structure. No source token or value is ever echoed."""
    raise SizingError(
        message,
        context={
            "key": key,
            "contribution": output,
            "column": column,
            "source_row_ordinal": row,
        },
    )


def convert_integer(token: str, *, key: str, output: str, column: str, row: int) -> int:
    text = token.strip()
    if not text or (text[0] in "+-" and len(text) == 1):
        _fail("a typed integer column has no value", key=key, output=output, column=column, row=row)
    body = text[1:] if text[0] in "+-" else text
    if not body.isdigit():
        _fail(
            "a typed integer column is not a strict integer",
            key=key,
            output=output,
            column=column,
            row=row,
        )
    value = int(text)
    if not -(2**63) <= value < 2**63:
        _fail(
            "a typed integer column overflows its declared width",
            key=key,
            output=output,
            column=column,
            row=row,
        )
    return value


def convert_decimal(
    token: str, *, key: str, output: str, column: str, row: int
) -> Decimal:
    """Convert one source lexeme into an exact scaled decimal, or block.

    ADR-0025 section 3: representability is decided from the lexeme's own sign, integer
    coefficient, and base-10 exponent using integer arithmetic only. Nothing here depends
    on the ambient decimal context, passes through a binary float, or rounds, so the same
    lexeme yields the same bytes whatever precision the caller has configured.
    """
    text = token.strip()
    if not text:
        _fail(
            "an exact decimal column has no value",
            key=key,
            output=output,
            column=column,
            row=row,
        )
    if _DECIMAL_LEXEME.match(text) is None:
        _fail(
            "an exact decimal column is not a decimal lexeme",
            key=key,
            output=output,
            column=column,
            row=row,
        )
    sign, coefficient, exponent = _lexeme_parts(
        text, key=key, output=output, column=column, row=row
    )
    # Rebase the coefficient onto the pinned scale with integer arithmetic.
    shift = exponent + DECIMAL_SCALE
    if shift >= 0:
        if shift > _MAX_DECIMAL_SHIFT:
            _fail(
                "an exact decimal column overflows the pinned precision",
                key=key,
                output=output,
                column=column,
                row=row,
            )
        unscaled = coefficient * 10**shift
    else:
        divisor = 10 ** (-shift)
        if coefficient % divisor:
            _fail(
                "an exact decimal column exceeds the pinned scale",
                key=key,
                output=output,
                column=column,
                row=row,
            )
        unscaled = coefficient // divisor
    if unscaled >= 10**DECIMAL_PRECISION:
        _fail(
            "an exact decimal column overflows the pinned precision",
            key=key,
            output=output,
            column=column,
            row=row,
        )
    # Constructing from an explicit digit tuple is exact and context independent.
    digits = tuple(int(character) for character in str(unscaled)) if unscaled else (0,)
    return Decimal((sign, digits, -DECIMAL_SCALE))


def _lexeme_parts(
    text: str, *, key: str, output: str, column: str, row: int
) -> tuple[int, int, int]:
    """The lexeme's sign, non-negative integer coefficient, and base-10 exponent."""
    body = text
    sign = 0
    if body[0] in "+-":
        sign = 1 if body[0] == "-" else 0
        body = body[1:]
    exponent = 0
    if "e" in body or "E" in body:
        body, _, exponent_text = body.replace("E", "e").partition("e")
        try:
            exponent = int(exponent_text)
        except ValueError:
            _fail(
                "an exact decimal column has no integer exponent",
                key=key,
                output=output,
                column=column,
                row=row,
            )
        if abs(exponent) > _MAX_DECIMAL_SHIFT:
            _fail(
                "an exact decimal column has an out-of-range exponent",
                key=key,
                output=output,
                column=column,
                row=row,
            )
    integer_part, _, fraction = body.partition(".")
    digits = f"{integer_part}{fraction}" or "0"
    if not digits.isdigit():
        _fail(
            "an exact decimal column is not a decimal lexeme",
            key=key,
            output=output,
            column=column,
            row=row,
        )
    return sign, int(digits), exponent - len(fraction)


def convert_timestamp_text(
    token: str, *, key: str, output: str, column: str, row: int
) -> int:
    """A declared UTC timestamp token becomes exact epoch milliseconds.

    ADR-0025 section 3: the conversion is integer calendar arithmetic relative to the UTC
    epoch. The float-returning `datetime` epoch helper is deliberately not used, so a
    pre-epoch instant is exact rather than rounded.
    """
    text = token.strip()
    if not text:
        _fail(
            "a typed timestamp column has no value",
            key=key,
            output=output,
            column=column,
            row=row,
        )
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00").replace(" ", "T"))
    except ValueError:
        _fail(
            "a typed timestamp column is not an ISO UTC instant",
            key=key,
            output=output,
            column=column,
            row=row,
        )
        raise  # pragma: no cover - _fail always raises
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    moment = moment.astimezone(UTC)
    days = moment.date().toordinal() - _EPOCH_ORDINAL
    seconds = days * 86_400 + moment.hour * 3_600 + moment.minute * 60 + moment.second
    return seconds * 1000 + moment.microsecond // 1000


def convert_dictionary(token: str, *, key: str, output: str, column: str, row: int) -> str:
    text = token.strip()
    if not text:
        _fail(
            "a dictionary column has no value",
            key=key,
            output=output,
            column=column,
            row=row,
        )
    return text


_CONVERTERS: Mapping[str, Any] = {
    KIND_INTEGER: convert_integer,
    KIND_DECIMAL: convert_decimal,
    KIND_TIMESTAMP_TEXT: convert_timestamp_text,
    KIND_DICTIONARY: convert_dictionary,
}


@dataclass(frozen=True, slots=True)
class TypedEnvelopeMeasurement:
    """What one real object costs in one required typed product, measured exactly.

    Payload is the encoded column-chunk total; footer, per-row-group metadata, and the
    fixed Parquet framing are separated so a tiny archive's file overhead is charged to
    its own projected partition and never multiplied across a whole family.
    """

    key: str
    family: str
    contribution: str
    product: str
    symbol: str
    economic_interval: str
    schema_kind: str
    compressed_archive_bytes: int
    extracted_member_bytes: int
    source_rows: int
    rows: int
    row_groups: int
    payload_bytes: int
    footer_bytes: int
    framing_bytes: int
    residual_bytes: int
    file_bytes: int
    parquet_sha256: str
    writer_identity: str
    pyarrow_version: str

    def payload_ratio(self) -> tuple[int, int]:
        return (self.payload_bytes, self.compressed_archive_bytes)

    def row_ratio(self) -> tuple[int, int]:
        return (self.rows, self.compressed_archive_bytes)

    def footer_per_row_group(self) -> int:
        """A conservative per-row-group metadata bound, never below the real footer."""
        overhead = max(self.footer_bytes, self.footer_bytes + self.residual_bytes)
        return ceil_div(overhead, self.row_groups)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "family": self.family,
            "contribution": self.contribution,
            "required_product": self.product,
            "symbol": self.symbol,
            "economic_interval": self.economic_interval,
            "schema_kind": self.schema_kind,
            "compressed_archive_bytes": self.compressed_archive_bytes,
            "extracted_member_bytes": self.extracted_member_bytes,
            "source_rows": self.source_rows,
            "rows": self.rows,
            "row_groups": self.row_groups,
            "typed_payload_bytes": self.payload_bytes,
            "footer_bytes": self.footer_bytes,
            "framing_bytes": self.framing_bytes,
            "residual_bytes": self.residual_bytes,
            "file_bytes": self.file_bytes,
            "footer_per_row_group_bytes": self.footer_per_row_group(),
            "parquet_sha256": self.parquet_sha256,
            "writer_identity": self.writer_identity,
            "pyarrow_version": self.pyarrow_version,
            "row_group_cap": SIZING_ROW_BATCH,
        }


def writer_identity() -> str:
    """The deterministic writer settings, named exactly as they are applied."""
    return (
        f"pyarrow{pa.__version__}_parquet{PARQUET_VERSION}_{PARQUET_COMPRESSION}"
        f"l{PARQUET_COMPRESSION_LEVEL}_rowgroup{SIZING_ROW_BATCH}_nostats_typed_v2"
    )


def _measure_parquet_file(path: Path) -> dict[str, int]:
    """Separate encoded column-chunk payload from footer, framing, and any residue."""
    file_bytes = int(path.stat().st_size)
    footer_bytes, framing_bytes = _parquet_footer_bytes(path)
    metadata = pq.ParquetFile(str(path)).metadata
    payload = 0
    for group in range(metadata.num_row_groups):
        row_group = metadata.row_group(group)
        for column in range(row_group.num_columns):
            payload += int(row_group.column(column).total_compressed_size)
    # Payload, footer, framing, and residue always account for the file exactly. The
    # residue is reported rather than hidden, and never lowers the overhead bound.
    residual = file_bytes - payload - footer_bytes - framing_bytes
    _require(
        payload > 0 and file_bytes > 0 and footer_bytes > 0,
        "a typed envelope does not separate into payload, footer, and framing",
        {"path": str(path)},
    )
    return {
        "file_bytes": file_bytes,
        "payload_bytes": payload,
        "footer_bytes": footer_bytes,
        "framing_bytes": framing_bytes,
        "residual_bytes": residual,
        "row_groups": int(metadata.num_row_groups),
        "rows": int(metadata.num_rows),
    }


def measure_typed_envelope(
    sample: CohortSample,
    *,
    payload: bytes,
    output: ProductContribution,
    destination: Path,
    schema_kind: str,
) -> TypedEnvelopeMeasurement:
    """Write one required typed product for one real object and measure it exactly."""
    _exact(
        output.family,
        sample.family,
        field_name="contribution_family",
        context={"key": sample.key, "contribution": output.name},
    )
    hint = sample.family.partition("/")[2]
    declared = list(KNOWN_ARCHIVE_SCHEMAS.get(hint, {}).get("headerless", ()))
    positions = {name: index for index, name in enumerate(declared)}
    schema = output.schema()
    member = safe_zip_member(payload, key=sample.key)
    rows = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = pq.ParquetWriter(
        str(destination),
        schema,
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
        version=PARQUET_VERSION,
        write_statistics=False,
        store_schema=True,
    )
    try:
        batch: list[list[str]] = []
        for row in _iter_source_rows(
            payload, key=sample.key, family=sample.family, schema_kind=schema_kind
        ):
            batch.append(row)
            if len(batch) >= SIZING_ROW_BATCH:
                _write_typed_batch(
                    writer,
                    schema,
                    batch,
                    sample=sample,
                    output=output,
                    positions=positions,
                    ordinal=rows,
                )
                rows += len(batch)
                batch = []
        if batch:
            _write_typed_batch(
                writer,
                schema,
                batch,
                sample=sample,
                output=output,
                positions=positions,
                ordinal=rows,
            )
            rows += len(batch)
    finally:
        writer.close()
    _require(rows > 0, "the retained sample parsed no rows", {"key": sample.key})
    measured = _measure_parquet_file(destination)
    _exact(
        measured["rows"],
        rows,
        field_name="typed_envelope_rows",
        context={"key": sample.key, "contribution": output.name},
    )
    return TypedEnvelopeMeasurement(
        key=sample.key,
        family=sample.family,
        contribution=output.name,
        product=output.product,
        symbol=sample.symbol,
        economic_interval=sample.economic_interval,
        schema_kind=schema_kind,
        compressed_archive_bytes=len(payload),
        extracted_member_bytes=int(member.file_size),
        source_rows=rows,
        rows=rows,
        row_groups=measured["row_groups"],
        payload_bytes=measured["payload_bytes"],
        footer_bytes=measured["footer_bytes"],
        framing_bytes=measured["framing_bytes"],
        residual_bytes=measured["residual_bytes"],
        file_bytes=measured["file_bytes"],
        parquet_sha256=compute_sha256(destination),
        writer_identity=writer_identity(),
        pyarrow_version=str(pa.__version__),
    )


def _write_typed_batch(
    writer: pq.ParquetWriter,
    schema: pa.Schema,
    batch: Sequence[Sequence[str]],
    *,
    sample: CohortSample,
    output: ProductContribution,
    positions: Mapping[str, int],
    ordinal: int,
) -> None:
    """One deterministic typed row group. A failed conversion blocks, never rounds."""
    columns: dict[str, list[Any]] = {}
    for column in output.columns:
        if column.kind == KIND_PARTITION_REF:
            # Compact partition-local lineage: the manifest resolves it exactly once.
            columns[column.name] = [0] * len(batch)
            continue
        if column.kind == KIND_ORDINAL:
            columns[column.name] = [ordinal + index for index in range(len(batch))]
            continue
        if not column.source_field:
            columns[column.name] = [sample.symbol] * len(batch)
            continue
        position = positions.get(column.source_field)
        _require(
            position is not None,
            "a typed column names a field the retained schema does not carry",
            {"key": sample.key, "contribution": output.name, "column": column.name},
        )
        assert position is not None
        convert = _CONVERTERS[column.kind]
        values: list[Any] = []
        for index, row in enumerate(batch):
            token = str(row[position])
            if column.nullable and not token.strip():
                values.append(None)
                continue
            values.append(
                convert(
                    token,
                    key=sample.key,
                    output=output.name,
                    column=column.name,
                    row=ordinal + index,
                )
            )
        columns[column.name] = values
    table = pa.Table.from_pydict(columns, schema=schema)
    writer.write_table(table, row_group_size=SIZING_ROW_BATCH)


UNKNOWN_RETRIEVAL_TIME: str = ""
UNKNOWN_AVAILABILITY: str = "source_availability_unknown"


_LINEAGE_IDENTITY_FIELDS: tuple[str, ...] = (
    "sha256",
    "byte_size",
    "family",
    "retrieval_time",
    "availability_semantics",
    "source_available_at",
)


def _lineage_identity(record: Mapping[str, Any]) -> tuple[Any, ...]:
    """The exact identity an accepted logical alias must reproduce to fold."""
    return (
        str(record.get("sha256") or ""),
        _optional_int(record.get("byte_size")),
        str(record.get("family") or ""),
        str(record.get("retrieval_time") or ""),
        str(record.get("availability_semantics") or ""),
        _optional_int(record.get("source_available_at")),
    )


def bind_sample_lineage(
    report: Mapping[str, Any],
    *,
    checkpoint: Mapping[str, Any],
    cohort: Sequence[CohortSample],
) -> dict[str, Any]:
    """Bind each physical key to its accepted report sample records and checkpoint row.

    ADR-0025 section 4: the accepted report carries more logical sample records than
    physical objects because ten keys appear in two sample regimes. A repeated key folds
    to one physical lineage record only when SHA-256, byte size, family, retrieval time,
    availability semantics, and source-availability time all agree; every logical role and
    regime label is preserved on the folded record. A disagreement, a missing binding, or
    a second checkpoint object for one key blocks before anything is published.

    Nothing here invents a retrieval time or an availability state: an unknown one is
    retained as explicitly unknown.
    """
    context = {"cohort": len(cohort)}
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    logical = 0
    for row in list(report.get("samples") or ()):
        _require(isinstance(row, dict), "a report sample record is not an object", context)
        record = dict(row)
        key = str(record.get("key") or "")
        _require(bool(key), "a report sample record has no key", context)
        grouped.setdefault(key, []).append(record)
        logical += 1
    folded = 0
    bindings: dict[str, dict[str, Any]] = {}
    for key, records in grouped.items():
        local = {**context, "key": key}
        identity = _lineage_identity(records[0])
        for other in records[1:]:
            candidate = _lineage_identity(other)
            for position, name in enumerate(_LINEAGE_IDENTITY_FIELDS):
                _require(
                    identity[position] == candidate[position],
                    "a repeated sample key disagrees about its physical lineage",
                    {**local, "field": name},
                )
            folded += 1
        roles = sorted(
            {str(item.get("product") or "") for item in records if item.get("product")}
        )
        regimes = sorted(
            {str(item.get("regime") or "") for item in records if item.get("regime")}
        )
        products: set[str] = set()
        for item in records:
            products.update(str(value) for value in (item.get("products") or ()))
        bindings[key] = {
            "source_key": key,
            "logical_records": len(records),
            "logical_roles": roles,
            "logical_regimes": regimes,
            "logical_products": sorted(products),
            "source_sha256": identity[0],
            "byte_size": identity[1],
            "family": identity[2],
            "retrieval_time": identity[3] or None,
            "retrieval_time_known": bool(identity[3]),
            "availability_semantics": identity[4],
            "source_available_at": identity[5],
        }
    proved: dict[str, dict[str, Any]] = {}
    for sample in cohort:
        local = {**context, "key": sample.key}
        record = bindings.get(sample.key)
        _require(
            record is not None,
            "a cohort sample has no accepted report sample record",
            local,
        )
        assert record is not None
        entry = checkpoint.get(sample.key)
        _require(
            isinstance(entry, dict),
            "a cohort sample has no checkpoint evidence",
            local,
        )
        assert isinstance(entry, dict)
        # Exactly one checkpoint object per physical key: a second one is a substitution.
        matching = [
            name
            for name, value in checkpoint.items()
            if str(name) == sample.key and isinstance(value, dict)
        ]
        _exact(
            len(matching),
            1,
            field_name="checkpoint_objects_per_key",
            context=local,
        )
        digest = str(entry.get("sha256") or "")
        _exact(
            record["source_sha256"], digest, field_name="report_sample.sha256", context=local
        )
        _exact(
            record["byte_size"],
            _optional_int(entry.get("byte_size")),
            field_name="report_sample.byte_size",
            context=local,
        )
        _exact(
            record["family"], sample.family, field_name="report_sample.family", context=local
        )
        _require(
            bool(record["availability_semantics"]),
            "an accepted report sample record has no availability semantics",
            local,
        )
        checkpoint_retrieval = str(entry.get("retrieval_time") or "")
        if checkpoint_retrieval and record["retrieval_time"]:
            _exact(
                record["retrieval_time"],
                checkpoint_retrieval,
                field_name="retrieval_time",
                context=local,
            )
        retrieval = record["retrieval_time"] or checkpoint_retrieval or None
        proved[sample.key] = {
            **record,
            "retrieval_time": retrieval,
            "retrieval_time_known": bool(retrieval),
            "checksum_authority": str(entry.get("provider_checksum_sha256") or ""),
            "checkpoint_status": str(entry.get("status") or ""),
        }
    decomposition = {
        "logical_records": logical,
        "physical_bindings": len(grouped),
        "folded_aliases": folded,
        "bound_cohort_keys": len(proved),
    }
    _exact(
        logical - len(grouped),
        folded,
        field_name="folded_alias_arithmetic",
        context=context,
    )
    return {"bindings": proved, "decomposition": decomposition}


def prove_accepted_lineage_decomposition(
    decomposition: Mapping[str, Any]
) -> dict[str, int]:
    """The accepted 106 logical / 96 physical / 10 folded decomposition, exactly."""
    context = {"source": "report.samples"}
    for field_name, expected in (
        ("logical_records", ACCEPTED_LOGICAL_SAMPLE_RECORDS),
        ("physical_bindings", ACCEPTED_PHYSICAL_SAMPLE_BINDINGS),
        ("folded_aliases", ACCEPTED_FOLDED_SAMPLE_ALIASES),
    ):
        _exact(
            _optional_int(decomposition.get(field_name)),
            expected,
            field_name=f"lineage.{field_name}",
            context=context,
        )
    return {
        "logical_records": ACCEPTED_LOGICAL_SAMPLE_RECORDS,
        "physical_bindings": ACCEPTED_PHYSICAL_SAMPLE_BINDINGS,
        "folded_aliases": ACCEPTED_FOLDED_SAMPLE_ALIASES,
        "rule": (
            "a repeated key folds only when sha256, byte size, family, retrieval time, "
            "availability semantics, and source-availability time all agree; every "
            "logical role and regime label is preserved on the folded record"
        ),
    }


def measure_partition_manifest(
    entries: Sequence[Mapping[str, Any]], *, destination: Path
) -> dict[str, Any]:
    """Measure one real partition-local lineage manifest, exactly.

    ADR-0025 section 5: a lineage manifest belongs to one required product / native
    symbol / UTC month partition. It carries one mapping per raw object feeding that
    partition, so a cross-product raw object is mapped in each product it feeds. This
    measures a real file; the projection charges its payload per mapping and its
    row-group/footer metadata and framing once per partition, never a cohort-wide file
    divided by its own row count.
    """
    _require(bool(entries), "a partition manifest has no raw object mapping", {})
    coinalyze = all(bool(item.get("provider_symbol")) for item in entries)
    schema = (
        COINALYZE_PARTITION_MANIFEST_SCHEMA
        if coinalyze
        else ARCHIVE_PARTITION_MANIFEST_SCHEMA
    )
    columns: dict[str, list[Any]] = {
            "raw_object_ref": [int(item["raw_object_ref"]) for item in entries],
            "required_product": [str(item["required_product"]) for item in entries],
            "component": [str(item["component"]) for item in entries],
            "native_symbol": [str(item["native_symbol"]) for item in entries],
            "utc_month": [str(item["utc_month"]) for item in entries],
            "source_key": [str(item["source_key"]) for item in entries],
            "source_state": [str(item["source_state"]) for item in entries],
            "source_sha256": [
                str(item["source_sha256"]) if item.get("source_sha256") else None
                for item in entries
            ],
            "checksum_authority": [
                str(item["checksum_authority"])
                if item.get("checksum_authority")
                else None
                for item in entries
            ],
            "retrieval_time": [
                None
                if item.get("retrieval_time") in (None, "")
                else str(item["retrieval_time"])
                for item in entries
            ],
            "availability_semantics": [
                str(item.get("availability_semantics") or UNKNOWN_AVAILABILITY)
                for item in entries
            ],
            "source_available_at": [
                _optional_int(item.get("source_available_at")) for item in entries
            ],
    }
    if coinalyze:
        columns.update(
            {
                "provider_symbol": [str(item["provider_symbol"]) for item in entries],
                "projected_response_bytes": [
                    _optional_int(item.get("projected_response_bytes")) for item in entries
                ],
                "projected_response_rows": [
                    _optional_int(item.get("projected_response_rows")) for item in entries
                ],
            }
        )
    else:
        columns["requirement_byte_size"] = [
            int(item["requirement_byte_size"]) for item in entries
        ]
    table = pa.Table.from_pydict(columns, schema=schema)
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = pq.ParquetWriter(
        str(destination),
        schema,
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
        version=PARQUET_VERSION,
        write_statistics=False,
        store_schema=True,
    )
    try:
        writer.write_table(table, row_group_size=SIZING_ROW_BATCH)
    finally:
        writer.close()
    measured = _measure_parquet_file(destination)
    known = sum(1 for item in entries if item.get("retrieval_time"))
    return {
        **measured,
        "mappings": len(entries),
        "payload_bytes_per_mapping": ceil_div(measured["payload_bytes"], len(entries)),
        "retrieval_time_known_mappings": known,
        "retrieval_time_unknown_mappings": len(entries) - known,
        "parquet_sha256": compute_sha256(destination),
        "writer_identity": writer_identity(),
        "manifest_kind": "coinalyze" if coinalyze else "archive",
        "schema": _schema_dict(schema),
    }


def _manifest_mapping_width(row: Mapping[str, Any]) -> int:
    """Uncompressed encoded-width ceiling for one manifest mapping."""
    width = 0
    for name, value in row.items():
        if name in {
            "raw_object_ref",
            "source_available_at",
            "requirement_byte_size",
            "projected_response_bytes",
            "projected_response_rows",
        }:
            width += INTEGER_WIDTH + int(value is None) * NULL_VALIDITY_WIDTH
        elif isinstance(value, str):
            width += len(value.encode("utf-8")) + VARIABLE_OFFSET_WIDTH
            if name in {
                "required_product",
                "component",
                "native_symbol",
                "utc_month",
                "source_state",
                "availability_semantics",
                "provider_symbol",
            }:
                width += DICTIONARY_INDEX_WIDTH
        elif value is None:
            width += NULL_VALIDITY_WIDTH
    return width


def build_retained_archive_bindings(
    *,
    credit: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    objects: Sequence[PhysicalObject],
    sample_bindings: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Join the exact Gate-2 credit keys to their re-proved archive evidence."""
    context = {"authority": "retained_gate2_credit"}
    by_key = {item.key: item for item in objects}
    _exact(
        len(by_key),
        len(objects),
        field_name="unique_requirement_keys",
        context=context,
    )
    keys = [str(key) for key in (credit.get("keys") or ())]
    _exact(
        len(keys),
        _optional_int(credit.get("valid_requirement_keys")),
        field_name="retained_credit.valid_requirement_keys",
        context=context,
    )
    digest = requirement_key_set_sha256(keys)
    _exact(
        digest,
        str(credit.get("key_set_sha256") or ""),
        field_name="retained_credit.key_set_sha256",
        context=context,
    )
    bindings: dict[str, dict[str, Any]] = {}
    for key in sorted(keys):
        local = {**context, "key": key}
        source = by_key.get(key)
        _require(
            source is not None,
            "a credited key names no selected or cost requirement",
            local,
        )
        assert source is not None
        entry = checkpoint.get(key)
        _require(
            isinstance(entry, dict),
            "a credited key has no exact checkpoint binding",
            local,
        )
        assert isinstance(entry, dict)
        _exact(
            str(entry.get("status") or ""),
            "complete",
            field_name="credited_checkpoint.status",
            context=local,
        )
        source_sha256 = str(entry.get("sha256") or "")
        checksum_authority = str(entry.get("provider_checksum_sha256") or "")
        _require(
            bool(source_sha256) and bool(checksum_authority),
            "a credited checkpoint binding has no hash authority",
            local,
        )
        # ADR-0023 keeps two distinct byte facts. The checkpoint value is the real
        # retained content-addressed object length, already rehashed against the bytes
        # on disk by prove_retained_acquisition_credit. PhysicalObject.byte_size is the
        # complete acquisition-requirement listing size. A retained cost witness is
        # routinely smaller than the full object it evidences, so equality here would be
        # false authority rather than a safety check.
        retained_byte_size = _positive_int(
            _optional_int(entry.get("byte_size")),
            field_name="credited_checkpoint.byte_size",
            context=local,
        )
        checkpoint_retrieval = str(entry.get("retrieval_time") or "") or None
        sample = sample_bindings.get(key)
        if sample is not None:
            _exact(
                str(sample.get("source_sha256") or ""),
                source_sha256,
                field_name="credited_sample.source_sha256",
                context=local,
            )
            # The accepted report sample records the same retained object, so it is
            # compared to the checkpoint's retained length, never to the requirement
            # listing size.
            _exact(
                _optional_int(sample.get("byte_size")),
                retained_byte_size,
                field_name="credited_sample.byte_size",
                context=local,
            )
            _exact(
                str(sample.get("family") or ""),
                source.family,
                field_name="credited_sample.family",
                context=local,
            )
            _exact(
                str(sample.get("checksum_authority") or ""),
                checksum_authority,
                field_name="credited_sample.checksum_authority",
                context=local,
            )
            retrieval_time = sample.get("retrieval_time")
            availability = str(sample.get("availability_semantics") or "")
            source_available_at = _optional_int(sample.get("source_available_at"))
            _require(
                bool(availability),
                "a credited sample binding has no availability semantics",
                local,
            )
        else:
            retrieval_time = checkpoint_retrieval
            availability = "requirement_listing_time_unknown"
            source_available_at = None
        bindings[key] = {
            "source_key": key,
            "source_sha256": source_sha256,
            "checksum_authority": checksum_authority,
            "retrieval_time": retrieval_time,
            "availability_semantics": availability,
            "source_available_at": source_available_at,
            # Both byte facts stay exact and separately named.
            "retained_byte_size": retained_byte_size,
            "requirement_byte_size": source.byte_size,
        }
    _exact(
        set(bindings),
        set(keys),
        field_name="retained_archive_binding_keys",
        context=context,
    )
    return bindings


def build_partition_lineage(
    retained_bindings: Mapping[str, Mapping[str, Any]],
    *,
    objects: Sequence[PhysicalObject],
    retained_credit_keys: Sequence[str],
) -> dict[tuple[str, str, str, str], list[dict[str, Any]]]:
    """The real lineage mapping set of every projected product partition.

    A mapping names the required product, the native symbol, the UTC month, the raw
    object or projected response receipt, its source hash, and its availability facts.
    A raw object feeding two products is mapped in each of those product partitions.
    """
    by_key = {item.key: item for item in objects}
    retained = {str(key): dict(value) for key, value in retained_bindings.items()}
    credit_keys = [str(key) for key in retained_credit_keys]
    _exact(
        set(retained),
        set(credit_keys),
        field_name="retained_lineage_credit_join",
        context={},
    )
    _exact(
        len(retained),
        len(credit_keys),
        field_name="retained_lineage_unique_credit_keys",
        context={},
    )
    for key, entry in retained.items():
        _exact(
            str(entry.get("source_key") or ""),
            key,
            field_name="retained_lineage.source_key",
            context={"key": key},
        )
        _require(
            key in by_key,
            "a lineage mapping names no requirement object",
            {"key": key},
        )
        _require(
            bool(entry.get("source_sha256"))
            and bool(entry.get("checksum_authority"))
            and bool(entry.get("availability_semantics")),
            "a retained archive binding is incomplete",
            {"key": key},
        )
    partitions: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for reference, source in enumerate(objects):
        bound = retained.get(source.key)
        for output in contributions_for_family(source.family):
            if output.product == PRODUCT_COST_CALIBRATION:
                partition_component = {
                    "daily_book_ticker": "retained_book_ticker",
                    "daily_book_depth": "retained_book_depth",
                }[output.component]
            else:
                partition_component = "target_product"
            month = utc_month(source.economic_interval)
            partition = (
                output.product,
                partition_component,
                source.symbol,
                month,
            )
            retained_state = bound is not None
            partitions.setdefault(partition, []).append(
                {
                    "raw_object_ref": reference,
                    "required_product": output.product,
                    "component": output.component,
                    "native_symbol": source.symbol,
                    "utc_month": month,
                    "source_key": source.key,
                    "source_state": (
                        RETAINED_RECEIPT_STATE
                        if retained_state
                        else PROJECTED_UNACQUIRED_STATE
                    ),
                    "source_sha256": (
                        str(bound["source_sha256"]) if retained_state else None
                    ),
                    "checksum_authority": (
                        str(bound.get("checksum_authority") or "") or None
                        if retained_state
                        else None
                    ),
                    "retrieval_time": (
                        bound.get("retrieval_time") if retained_state else None
                    ),
                    "availability_semantics": (
                        str(bound.get("availability_semantics") or UNKNOWN_AVAILABILITY)
                        if retained_state
                        else "requirement_listing_proves_projected_object"
                    ),
                    "source_available_at": (
                        _optional_int(bound.get("source_available_at"))
                        if retained_state
                        else None
                    ),
                    "requirement_byte_size": source.byte_size,
                }
            )
    _require(bool(partitions), "no product partition carries a lineage mapping", {})
    return partitions


def reconcile_archive_lineage(
    partitions: Mapping[
        tuple[str, str, str, str], Sequence[Mapping[str, Any]]
    ],
    *,
    requirement_keys: Sequence[str],
    retained_credit_keys: Sequence[str],
    coefficient_keys: Sequence[str],
) -> dict[str, Any]:
    """Fail closed unless projected archive states exactly partition the requirement."""
    required = set(str(key) for key in requirement_keys)
    credited = set(str(key) for key in retained_credit_keys)
    _exact(
        len(required),
        len(requirement_keys),
        field_name="archive_lineage_unique_requirement_keys",
        context={},
    )
    _require(
        credited <= required,
        "a retained archive key is outside the requirement",
        {"extra_keys": sorted(credited - required)[:8]},
    )
    states: dict[str, str] = {}
    for mappings in partitions.values():
        for row in mappings:
            key = str(row.get("source_key") or "")
            _require(
                key in required,
                "an archive lineage row is outside the requirement",
                {"key": key},
            )
            state = str(row.get("source_state") or "")
            previous = states.setdefault(key, state)
            _exact(
                state,
                previous,
                field_name="archive_lineage.consistent_source_state",
                context={"key": key},
            )
    _exact(
        set(states),
        required,
        field_name="archive_lineage_complete_requirement_keys",
        context={},
    )
    for key, observed in states.items():
        expected = (
            RETAINED_RECEIPT_STATE
            if key in credited
            else PROJECTED_UNACQUIRED_STATE
        )
        _exact(
            observed,
            expected,
            field_name="archive_lineage.source_state",
            context={"key": key},
        )
    retained = sorted(
        key for key, observed in states.items() if observed == RETAINED_RECEIPT_STATE
    )
    _exact(
        retained,
        sorted(credited),
        field_name="retained_archive_key_set",
        context={},
    )
    coefficient_only = set(str(key) for key in coefficient_keys) - credited
    coefficient_only_retained = coefficient_only & set(retained)
    _exact(
        len(coefficient_only_retained),
        0,
        field_name="coefficient_only_keys_marked_retained",
        context={"keys": sorted(coefficient_only_retained)[:8]},
    )
    return {
        "retained_archive_requirement_keys": len(retained),
        "retained_archive_key_set_sha256": requirement_key_set_sha256(retained),
        "projected_unacquired_archive_requirement_keys": len(required) - len(retained),
        "coefficient_only_archive_keys": len(coefficient_only),
        "coefficient_only_keys_marked_retained": 0,
        "rule": (
            "retained archive state is an exact join to the re-proved Gate-2 credit "
            "key set; the coefficient cohort supplies no retention authority"
        ),
    }


def coinalyze_partition_lineage(
    *,
    partitions: Sequence[tuple[str, str]],
    receipt_sha256: str,
    receipt_endpoint: str,
    identities: CoinalyzeIdentityMap,
    availability: str,
    retrieval_time: str | None,
    retained_partitions: Sequence[tuple[str, str]] = (),
) -> dict[tuple[str, str, str, str], list[dict[str, Any]]]:
    """Coinalyze partitions map their local reference to the response receipt.

    Each symbol/month partition carries the retained or projected response receipt and
    the proved provider/native identity pair, under the same lineage contract as the
    archive partitions.
    """
    retained = set(retained_partitions)
    mapped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for reference, (symbol, month) in enumerate(sorted(set(partitions))):
        provider = identities.provider_for(symbol, context={"endpoint": receipt_endpoint})
        is_retained = (symbol, month) in retained
        mapped[(
            PRODUCT_LIQUIDATION_OBSERVED_DAILY,
            "observed_liquidation",
            symbol,
            month,
        )] = [
            {
                "raw_object_ref": reference,
                "required_product": PRODUCT_LIQUIDATION_OBSERVED_DAILY,
                "component": "observed_liquidation",
                "source_key": f"{receipt_endpoint}#{symbol}",
                "source_state": (
                    RETAINED_RECEIPT_STATE if is_retained else PROJECTED_UNACQUIRED_STATE
                ),
                "source_sha256": receipt_sha256 if is_retained else None,
                "checksum_authority": receipt_sha256 if is_retained else None,
                "retrieval_time": retrieval_time if is_retained else None,
                "availability_semantics": (
                    availability if is_retained else "projected_response_receipt"
                ),
                "source_available_at": None,
                "native_symbol": symbol,
                "provider_symbol": provider,
                "utc_month": month,
                "projected_response_bytes": None,
                "projected_response_rows": None,
            }
        ]
    return mapped


def retained_coinalyze_partition_keys(
    evidence: Sequence[CoinalyzeEvidence], *, identities: CoinalyzeIdentityMap
) -> tuple[tuple[str, str], ...]:
    """Exact native/month coverage carried by the retained liquidation witness."""
    witness = next(
        item for item in evidence if item.role == "liquidation_charge_witness"
    )
    measured = measure_liquidation_response(witness.payload, endpoint=witness.endpoint)
    return tuple(
        sorted(
            {
                (
                    identities.native_for(provider, context={"endpoint": witness.endpoint}),
                    _utc_month_of_day(_utc_day_from_ms(int(point["event_time_ms"]))),
                )
                for provider, points in measured["series"]
                for point in points
            }
        )
    )


@dataclass(frozen=True, slots=True)
class LineageManifestModel:
    """The partition-local lineage charge, separated into its three real parts."""

    payload_bytes_per_mapping: int
    footer_per_row_group_bytes: int
    framing_bytes: int
    witness_partitions: tuple[Mapping[str, Any], ...]
    coinalyze_payload_bytes_per_mapping: int | None = None
    coinalyze_footer_per_row_group_bytes: int | None = None
    coinalyze_framing_bytes: int | None = None
    coinalyze_witness_partitions: tuple[Mapping[str, Any], ...] = ()

    def partition_bytes(self, mappings: int, *, kind: str = "archive") -> dict[str, int]:
        _require(
            mappings > 0,
            "a product partition has no lineage mapping",
            {"mappings": mappings},
        )
        _require(kind in {"archive", "coinalyze"}, "unknown lineage manifest kind", {"kind": kind})
        row_groups = max(1, ceil_div(mappings, SIZING_ROW_BATCH))
        payload_rate = (
            self.payload_bytes_per_mapping
            if kind == "archive" or self.coinalyze_payload_bytes_per_mapping is None
            else self.coinalyze_payload_bytes_per_mapping
        )
        footer = (
            self.footer_per_row_group_bytes
            if kind == "archive" or self.coinalyze_footer_per_row_group_bytes is None
            else self.coinalyze_footer_per_row_group_bytes
        )
        framing = (
            self.framing_bytes
            if kind == "archive" or self.coinalyze_framing_bytes is None
            else self.coinalyze_framing_bytes
        )
        payload = mappings * payload_rate
        overhead = row_groups * footer + framing
        return {
            "mappings": mappings,
            "row_groups": row_groups,
            "payload_bytes": payload,
            "overhead_bytes": overhead,
            "bytes": payload + overhead,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "payload_bytes_per_mapping": self.payload_bytes_per_mapping,
            "footer_per_row_group_bytes": self.footer_per_row_group_bytes,
            "framing_bytes_per_partition": self.framing_bytes,
            "witness_partitions": [dict(item) for item in self.witness_partitions],
            "archive_schema": _schema_dict(ARCHIVE_PARTITION_MANIFEST_SCHEMA),
            "coinalyze": {
                "payload_bytes_per_mapping": (
                    self.coinalyze_payload_bytes_per_mapping
                    if self.coinalyze_payload_bytes_per_mapping is not None
                    else self.payload_bytes_per_mapping
                ),
                "footer_per_row_group_bytes": (
                    self.coinalyze_footer_per_row_group_bytes
                    if self.coinalyze_footer_per_row_group_bytes is not None
                    else self.footer_per_row_group_bytes
                ),
                "framing_bytes_per_partition": (
                    self.coinalyze_framing_bytes
                    if self.coinalyze_framing_bytes is not None
                    else self.framing_bytes
                ),
                "schema": _schema_dict(COINALYZE_PARTITION_MANIFEST_SCHEMA),
                "witness_partitions": [
                    dict(item) for item in self.coinalyze_witness_partitions
                ],
            },
            "equation": (
                "per partition: mappings * payload_bytes_per_mapping + row_groups * "
                "footer_per_row_group + framing; every partition pays its own overhead "
                "and no cohort-global manifest copy exists"
            ),
        }


def model_partition_lineage(
    partitions: Mapping[tuple[str, str, str, str], list[dict[str, Any]]],
    *,
    staging: Path,
    coinalyze_partitions: Mapping[
        tuple[str, str, str, str], list[dict[str, Any]]
    ] | None = None,
) -> LineageManifestModel:
    """Measure two real, differently sized partition manifests.

    The smallest and largest real partitions are written and measured. Their difference
    isolates the conservative per-mapping payload; each one's own footer and framing is
    the fixed per-partition overhead every projected partition pays in full.
    """
    _require(bool(partitions), "a lineage model has no partition", {})
    def _measure_kind(
        values: Mapping[tuple[str, str, str, str], list[dict[str, Any]]],
        *,
        prefix: str,
    ) -> tuple[int, int, int, tuple[Mapping[str, Any], ...]]:
        ordered = sorted(values.items(), key=lambda item: (len(item[1]), item[0]))
        selected = (ordered[0], ordered[-1])
        witnesses: list[Mapping[str, Any]] = []
        measurements: list[dict[str, Any]] = []
        for index, (partition, mappings) in enumerate(selected):
            measured = measure_partition_manifest(
                mappings,
                destination=staging / f"lineage-{prefix}-partition-{index}.parquet",
            )
            measurements.append(measured)
            witnesses.append(
                {
                    "required_product": partition[0],
                    "component": partition[1],
                    "native_symbol": partition[2],
                    "utc_month": partition[3],
                    "mappings": len(mappings),
                    "file_bytes": int(measured["file_bytes"]),
                    "payload_bytes": int(measured["payload_bytes"]),
                    "footer_bytes": int(measured["footer_bytes"]),
                    "framing_bytes": int(measured["framing_bytes"]),
                }
            )
        logical_width_bound = max(
            _manifest_mapping_width(row)
            for mappings in values.values()
            for row in mappings
        )
        payload = max(
            logical_width_bound,
            max(int(item["payload_bytes_per_mapping"]) for item in measurements),
        )
        footer = max(
            ceil_div(
                max(
                    int(item["footer_bytes"]),
                    int(item["footer_bytes"]) + int(item["residual_bytes"]),
                ),
                max(int(item["row_groups"]), 1),
            )
            for item in measurements
        )
        framing = max(int(item["framing_bytes"]) for item in measurements)
        return payload, footer, framing, tuple(witnesses)

    payload_per_mapping, footer_per_row_group, framing, archive_witnesses = _measure_kind(
        partitions, prefix="archive"
    )
    coinalyze_values = dict(coinalyze_partitions or {})
    if coinalyze_values:
        c_payload, c_footer, c_framing, c_witnesses = _measure_kind(
            coinalyze_values, prefix="coinalyze"
        )
    else:
        c_payload = c_footer = c_framing = None
        c_witnesses = ()
    return LineageManifestModel(
        payload_bytes_per_mapping=payload_per_mapping,
        footer_per_row_group_bytes=footer_per_row_group,
        framing_bytes=framing,
        witness_partitions=archive_witnesses,
        coinalyze_payload_bytes_per_mapping=c_payload,
        coinalyze_footer_per_row_group_bytes=c_footer,
        coinalyze_framing_bytes=c_framing,
        coinalyze_witness_partitions=c_witnesses,
    )


def classify_membership(report: Mapping[str, Any]) -> dict[str, Any]:
    """Split the report's classifications into accepted identities and exclusions.

    The pinned report classifies every discovered name. Only the affirmatively confirmed
    perpetuals are release membership; the rest are retained as proved exclusion evidence
    and never create a fee gap, a membership row, or a sizing identity.
    """
    context = {"source": "report.membership.classifications"}
    rows = [
        dict(item)
        for item in (dict(report.get("membership") or {}).get("classifications") or ())
        if isinstance(item, dict)
    ]
    _require(bool(rows), "the accepted report carries no membership row", context)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        symbol = str(row.get("symbol") or "")
        _require(bool(symbol), "a membership classification has no symbol", context)
        if row.get("accepted") is True:
            _exact(
                str(row.get("membership_class") or MEMBERSHIP_ACCEPTED_CLASS),
                MEMBERSHIP_ACCEPTED_CLASS,
                field_name="membership_class",
                context={**context, "symbol": symbol},
            )
            accepted.append(row)
        else:
            rejected.append(row)
    symbols = [str(row.get("symbol") or "") for row in accepted]
    _require(
        len(set(symbols)) == len(symbols),
        "the accepted report repeats an accepted membership identity",
        context,
    )
    _exact(
        len(rows),
        ACCEPTED_MEMBERSHIP_CLASSIFICATIONS,
        field_name="membership_classifications",
        context=context,
    )
    _exact(
        len(accepted),
        ACCEPTED_MEMBERSHIP_IDENTITIES,
        field_name="accepted_membership_identities",
        context=context,
    )
    _exact(
        len(rejected),
        ACCEPTED_REJECTED_MEMBERSHIP_ROWS,
        field_name="rejected_membership_rows",
        context=context,
    )
    return {
        "accepted": tuple(accepted),
        "rejected": tuple(rejected),
        "counts": {
            "membership_classifications": len(rows),
            "accepted_membership_identities": len(accepted),
            "rejected_membership_rows": len(rejected),
        },
        "rule": (
            "only affirmatively confirmed perpetuals are release membership; rejected "
            "classifications are exclusion evidence and size no accepted row"
        ),
    }


def contract_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    """One accepted identity's real contract facts, taken only from its own evidence.

    Nothing is inferred from a ticker suffix and nothing defaults to USDT. Two accepted
    evidence records that disagree about a stable contract fact block rather than letting
    this pick a convenient one.
    """
    symbol = str(row.get("symbol") or "")
    context = {"symbol": symbol}
    records = [dict(item) for item in (row.get("evidence") or ()) if isinstance(item, dict)]
    _require(bool(records), "an accepted membership row has no evidence", context)
    resolved: dict[str, Any] = {}
    for field_name in (
        "contract_type",
        "status",
        "underlying_type",
        "base_asset",
        "quote_asset",
        "margin_asset",
        "pair",
        "onboard_ms",
        "delivery_ms",
        "closed_observed_ms",
        "semantics_state",
    ):
        values = [
            record[field_name]
            for record in records
            if record.get(field_name) not in (None, "")
        ]
        if not values:
            resolved[field_name] = None
            continue
        first = values[0]
        for candidate in values[1:]:
            _require(
                candidate == first,
                "accepted membership evidence disagrees about a contract fact",
                {**context, "field": field_name},
            )
        resolved[field_name] = first
    evidence = records[0]
    detailed = all(
        bool(resolved.get(required))
        for required in ("contract_type", "base_asset", "quote_asset", "margin_asset")
    )
    if detailed:
        metadata_state = MEMBERSHIP_DETAILED_STATE
        evidence_class = str(evidence.get("kind") or "")
        evidence_source = str(evidence.get("endpoint") or "")
        _require(
            bool(evidence_class) and bool(evidence_source),
            "detailed contract evidence has no exact class or source",
            context,
        )
    else:
        _exact(
            str(evidence.get("kind") or ""),
            FUNDING_ONLY_EVIDENCE_CLASS,
            field_name="funding_only_evidence_class",
            context=context,
        )
        _exact(
            str(evidence.get("semantics") or ""),
            FUNDING_ONLY_SEMANTICS,
            field_name="funding_only_semantics",
            context=context,
        )
        _require(
            "monthly/fundingRate" in set(str(item) for item in evidence.get("families") or ()),
            "funding-only membership has no realized-funding family evidence",
            context,
        )
        evidence_source = str(evidence.get("example_key") or "")
        _require(
            bool(evidence_source),
            "funding-only membership has no exact evidence source",
            context,
        )
        _require(
            not any(
                resolved.get(field_name) not in (None, "")
                for field_name in (
                    "status",
                    "underlying_type",
                    "base_asset",
                    "quote_asset",
                    "margin_asset",
                    "pair",
                    "onboard_ms",
                    "delivery_ms",
                    "closed_observed_ms",
                )
            ),
            "funding-only membership mixes unavailable contract terms",
            context,
        )
        # Realized funding proves only perpetual membership. No ticker term is parsed.
        resolved["contract_type"] = "PERPETUAL"
        resolved["semantics_state"] = FUNDING_ONLY_SEMANTICS
        metadata_state = MEMBERSHIP_FUNDING_ONLY_STATE
        evidence_class = FUNDING_ONLY_EVIDENCE_CLASS
    return {
        "native_symbol": symbol,
        "membership_class": str(row.get("membership_class") or ""),
        "in_archive": row.get("in_archive") is True,
        "in_current_exchange": row.get("in_current_exchange") is True,
        "contract_type": str(resolved["contract_type"]),
        "contract_metadata_state": metadata_state,
        "contract_evidence_class": evidence_class,
        "contract_evidence_source": evidence_source,
        "contract_status": str(resolved["status"]) if resolved.get("status") else None,
        "underlying_type": (
            str(resolved["underlying_type"]) if resolved.get("underlying_type") else None
        ),
        "base_asset": str(resolved["base_asset"]) if resolved.get("base_asset") else None,
        "quote_asset": (
            str(resolved["quote_asset"]) if resolved.get("quote_asset") else None
        ),
        "margin_asset": (
            str(resolved["margin_asset"]) if resolved.get("margin_asset") else None
        ),
        "pair": str(resolved["pair"]) if resolved.get("pair") else None,
        "onboard_ms": _optional_int(resolved.get("onboard_ms")),
        "delivery_ms": _optional_int(resolved.get("delivery_ms")),
        "closed_observed_ms": _optional_int(resolved.get("closed_observed_ms")),
        "semantics_state": str(resolved.get("semantics_state") or ""),
        "evidence_records": len(records),
    }


def _source_gap_row(gap: Mapping[str, Any]) -> dict[str, Any]:
    """One accepted source-gap record, preserved losslessly in typed columns.

    Every accepted field survives: the complete family list, the observed bounds as
    observed bounds, the family first/last evidence, and the lifecycle periods. Nothing
    is truncated to a first family and no observed bound is renamed a missing bound.
    """
    record = dict(gap)
    families = [str(item) for item in (record.get("families") or ())]
    missing = [str(item) for item in (record.get("missing_months") or ())]
    return {
        "required_product": str(record.get("product") or ""),
        "native_symbol": str(record.get("symbol") or ""),
        "family_group": str(record.get("family_group") or ""),
        "families": families,
        "family_count": len(families),
        "gap_kind": str(record.get("kind") or ""),
        "gap_status": str(record.get("status") or ""),
        "blocking": bool(record.get("blocking")),
        "observed_months": _optional_int(record.get("observed_months")),
        "first_observed_period": str(record.get("first_observed") or ""),
        "last_observed_period": str(record.get("last_observed") or ""),
        "family_first_observed_period": str(record.get("family_first_observed") or ""),
        "family_last_observed_period": str(record.get("family_last_observed") or ""),
        "onboard_period": str(record.get("onboard_period") or ""),
        "close_period": str(record.get("close_period") or ""),
        "missing_months": missing,
        "missing_month_count": _optional_int(record.get("missing_month_count")),
        "objects": _optional_int(record.get("objects")),
        "explained_by": str(record.get("explained_by") or ""),
    }


def prove_coverage_authority(report: Mapping[str, Any]) -> dict[str, Any]:
    """Read the complete accepted coverage evidence, never the Coinalyze gaps alone.

    Three counts stay separate and none replaces another: the accepted product-scoped
    source-gap records, the accepted product/symbol typed-gap memberships, and one
    ADR-0026 fee-authority gap for each accepted membership identity.
    """
    context = {"source": "report.product_matrix"}
    matrix = list(report.get("product_matrix") or ())
    _require(bool(matrix), "the accepted report carries no product matrix", context)
    source_gaps: list[dict[str, Any]] = []
    typed_memberships: list[dict[str, str]] = []
    products_with_gaps: set[str] = set()
    family_histogram: dict[int, int] = {}
    for row in matrix:
        _require(isinstance(row, dict), "a product matrix row is not an object", context)
        record = dict(row)
        product = str(record.get("product") or "")
        _require(bool(product), "a product matrix row has no product", context)
        for gap in record.get("universe_coverage_gaps") or ():
            _require(
                isinstance(gap, dict),
                "a universe coverage gap is not an object",
                {**context, "product": product},
            )
            typed_gap = _source_gap_row({"product": product, **dict(gap)})
            source_gaps.append(typed_gap)
            products_with_gaps.add(product)
            count = int(typed_gap["family_count"])
            family_histogram[count] = family_histogram.get(count, 0) + 1
        for symbol in record.get("typed_gap_symbols") or ():
            typed_memberships.append(
                {"required_product": product, "native_symbol": str(symbol)}
            )
    _exact(
        len(source_gaps),
        ACCEPTED_SOURCE_COVERAGE_GAPS,
        field_name="accepted_source_coverage_gaps",
        context=context,
    )
    _exact(
        len(typed_memberships),
        ACCEPTED_TYPED_GAP_MEMBERSHIPS,
        field_name="accepted_typed_gap_memberships",
        context=context,
    )
    membership = classify_membership(report)
    # ADR-0026: exactly one typed fee-authority gap per accepted membership identity.
    fee_gaps = [
        {
            "required_product": PRODUCT_COST_CALIBRATION,
            "native_symbol": str(item.get("symbol") or ""),
            "gap_kind": FEE_GAP_KIND,
            "gap_status": FEE_GAP_KIND,
            "blocking": False,
            "authority_class": FEE_AUTHORITY_CLASS,
            "explained_by": "no_free_reproducible_historical_fee_authority",
        }
        for item in membership["accepted"]
    ]
    _exact(
        len(fee_gaps),
        ACCEPTED_FEE_AUTHORITY_GAPS,
        field_name="fee_authority_gaps",
        context=context,
    )
    known_rows = len(source_gaps) + len(fee_gaps)
    _exact(
        known_rows,
        ACCEPTED_KNOWN_COVERAGE_ROWS,
        field_name="known_coverage_rows",
        context=context,
    )
    return {
        "membership": membership,
        "source_gaps": tuple(source_gaps),
        "fee_gaps": tuple(fee_gaps),
        "typed_gap_memberships": tuple(typed_memberships),
        "counts": {
            **dict(membership["counts"]),
            "accepted_source_coverage_gaps": len(source_gaps),
            "accepted_typed_gap_memberships": len(typed_memberships),
            "fee_authority_gaps": len(fee_gaps),
            "known_coverage_rows": known_rows,
            "products_with_source_gaps": len(products_with_gaps),
            "official_historical_fee_rows": ACCEPTED_OFFICIAL_FEE_ROWS,
            "fee_scenario_policy_rows": len(FEE_SCENARIOS),
            "source_gap_family_histogram": dict(sorted(family_histogram.items())),
        },
        "rule": (
            "the known minimum is the accepted product-scoped source gaps plus one "
            "fee-authority gap per accepted membership identity; the typed-gap "
            "memberships are a separate proved count and replace neither"
        ),
    }


def quality_gap_reservation(expected_rows: int) -> int:
    """The maximum number of disjoint missing runs in an ordered expected grid."""
    _require(
        expected_rows >= 0,
        "a quality gap reservation has no expected row ceiling",
        {"expected_rows": expected_rows},
    )
    return ceil_div(expected_rows, 2)


def fee_scenario_rows() -> tuple[dict[str, Any], ...]:
    """The two ADR-0026 policy rows. Neither is a historical FEE-001 observation."""
    rows: list[dict[str, Any]] = []
    for scenario in FEE_SCENARIOS:
        maker = convert_decimal(
            str(scenario["maker_rate"]),
            key=FEE_POLICY_KNOWN_AT,
            output=PRODUCT_COST_CALIBRATION,
            column="maker_rate",
            row=len(rows),
        )
        taker = convert_decimal(
            str(scenario["taker_rate"]),
            key=FEE_POLICY_KNOWN_AT,
            output=PRODUCT_COST_CALIBRATION,
            column="taker_rate",
            row=len(rows),
        )
        rows.append(
            {
                "scenario_id": str(scenario["scenario_id"]),
                "role": str(scenario["role"]),
                "scope": FEE_SCENARIO_SCOPE,
                "authority_class": FEE_AUTHORITY_CLASS,
                "policy_known_at": FEE_POLICY_KNOWN_AT,
                "maker_rate": maker,
                "taker_rate": taker,
                "charges_each_side": True,
                "maker_credit_enabled": False,
                "rebates_enabled": False,
                "vip_discounts_enabled": False,
                "referral_discounts_enabled": False,
                "bnb_discount_enabled": False,
                "source_basis": (
                    "official current commissionRate example and the preregistered "
                    "fixed-fee convention; no past Binance rate is claimed"
                ),
            }
        )
    return tuple(rows)




def measure_fixed_schema_product(
    *,
    product: str,
    schema: pa.Schema,
    columns: Mapping[str, Sequence[Any]],
    destination: Path,
    component: str | None = None,
) -> dict[str, Any]:
    """Measure one non-archive required product from its own real evidence rows.

    ADR-0025 keeps the parent required product and the measurement component apart. A
    component of a required product names that product here and carries its own component
    label; a measurement dictionary key never creates an additional required product.
    """
    rows = len(next(iter(columns.values()), ()))
    _require(
        rows > 0,
        "a required product has no row to measure",
        {"required_product": product},
    )
    table = pa.Table.from_pydict(dict(columns), schema=schema)
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = pq.ParquetWriter(
        str(destination),
        schema,
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
        version=PARQUET_VERSION,
        write_statistics=False,
        store_schema=True,
    )
    try:
        writer.write_table(table, row_group_size=SIZING_ROW_BATCH)
    finally:
        writer.close()
    measured = _measure_parquet_file(destination)
    return {
        **measured,
        "required_product": product,
        **({"component": component} if component else {}),
        "measured_rows": rows,
        "bytes_per_row": ceil_div(measured["payload_bytes"], rows),
        "schema": _schema_dict(schema),
        "parquet_sha256": compute_sha256(destination),
        "writer_identity": writer_identity(),
    }


def measure_zero_row_schema_descriptor(
    *, product: str, component: str, schema: pa.Schema, destination: Path
) -> dict[str, Any]:
    """Measure the real catalog-loadable descriptor for an authoritative zero-row schema."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_batches([], schema=schema)
    pq.write_table(
        table,
        str(destination),
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
        version=PARQUET_VERSION,
        write_statistics=False,
        store_schema=True,
    )
    file_bytes = int(destination.stat().st_size)
    footer_bytes, framing_bytes = _parquet_footer_bytes(destination)
    metadata = pq.ParquetFile(str(destination)).metadata
    _exact(metadata.num_rows, 0, field_name="official_fee_schema_rows", context={})
    measured = {
        "file_bytes": file_bytes,
        "payload_bytes": 0,
        "footer_bytes": footer_bytes,
        "framing_bytes": framing_bytes,
        "residual_bytes": file_bytes - footer_bytes - framing_bytes,
        "row_groups": int(metadata.num_row_groups),
        "rows": 0,
    }
    return {
        **measured,
        "required_product": product,
        "component": component,
        "measured_rows": 0,
        "bytes_per_row": 0,
        "schema": _schema_dict(schema),
        "schema_sha256": _sha256_bytes(canonical_json({"schema": _schema_dict(schema)})),
        "parquet_sha256": compute_sha256(destination),
        "writer_identity": writer_identity(),
    }


def _typed_value_width(column: TypedColumn, value: Any) -> int:
    if value is None:
        return NULL_VALIDITY_WIDTH
    if column.kind in {KIND_INTEGER, KIND_TIMESTAMP_TEXT, KIND_ORDINAL}:
        return INTEGER_WIDTH
    if column.kind == KIND_PARTITION_REF:
        return 4
    if column.kind == KIND_DECIMAL:
        return 16
    if column.kind == KIND_BOOLEAN:
        return 1
    if column.kind == KIND_STRING_LIST:
        return VARIABLE_OFFSET_WIDTH + sum(
            VARIABLE_OFFSET_WIDTH + len(str(item).encode("utf-8")) for item in value
        )
    encoded = len(str(value).encode("utf-8")) + VARIABLE_OFFSET_WIDTH
    if column.kind == KIND_DICTIONARY:
        encoded += DICTIONARY_INDEX_WIDTH
    return encoded


def measure_maximum_width_product(
    *,
    product: str,
    columns: Sequence[TypedColumn],
    rows: Sequence[Mapping[str, Any]],
    destination: Path,
) -> dict[str, Any]:
    """Traverse every row and use a per-field maximum-width witness when it is large."""
    _require(bool(rows), "a maximum-width product has no row", {"required_product": product})
    if len(rows) <= SIZING_ROW_BATCH:
        return measure_fixed_schema_product(
            product=product,
            schema=_schema_of(columns),
            columns=_column_values(columns, rows),
            destination=destination,
        )
    widest: dict[str, Any] = {}
    maxima: dict[str, int] = {}
    for row in rows:
        for column in columns:
            _require(
                column.name in row,
                "a maximum-width row is missing a declared column",
                {"required_product": product, "column": column.name},
            )
            width = _typed_value_width(column, row[column.name])
            if column.name not in maxima or width > maxima[column.name]:
                maxima[column.name] = width
                widest[column.name] = row[column.name]
    measured = measure_fixed_schema_product(
        product=product,
        schema=_schema_of(columns),
        columns=_column_values(columns, [widest]),
        destination=destination,
    )
    row_width_bound = sum(maxima.values())
    return {
        **measured,
        "measured_rows": len(rows),
        "bytes_per_row": max(int(measured["bytes_per_row"]), row_width_bound),
        "width_model": {
            "rows_traversed": len(rows),
            "per_field_maximum_encoded_widths": maxima,
            "maximum_row_bytes": row_width_bound,
            "rule": (
                "every projected value was traversed; independently greatest field "
                "widths form a conservative row that covers every omitted combination"
            ),
        },
    }


def project_fixed_schema_product(
    measured: Mapping[str, Any],
    *,
    rows: int,
    partitions: int,
    partition_rows: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Project one non-archive product from its own measured per-row and file costs."""
    context = {"required_product": str(measured.get("required_product") or "")}
    # The component label travels with the measurement so the fixed-schema, coverage,
    # and cost-component receipt views cannot read a component key as a product.
    component = str(measured.get("component") or "")
    _require(rows >= 0 and partitions > 0, "a fixed-schema projection is empty", context)
    if partition_rows is not None:
        _exact(
            len(partition_rows),
            partitions,
            field_name="fixed_partition_count",
            context=context,
        )
        _exact(sum(partition_rows), rows, field_name="fixed_partition_rows", context=context)
        rows_by_partition = [int(value) for value in partition_rows]
    else:
        rows_by_partition = [rows] + [0] * (partitions - 1)
    footer_per_row_group = ceil_div(
        int(measured["footer_bytes"]) + int(measured.get("residual_bytes") or 0),
        max(int(measured.get("row_groups") or 0), 1),
    )
    framing_per_file = int(measured["framing_bytes"])
    row_groups = sum(
        max(1, ceil_div(max(value, 1), SIZING_ROW_BATCH))
        for value in rows_by_partition
    )
    payload = int(measured["bytes_per_row"]) * rows
    overhead = row_groups * footer_per_row_group + partitions * framing_per_file
    largest = max(
        int(measured["bytes_per_row"]) * value
        + max(1, ceil_div(max(value, 1), SIZING_ROW_BATCH)) * footer_per_row_group
        + framing_per_file
        for value in rows_by_partition
    )
    return {
        **dict(context),
        **({"component": component} if component else {}),
        "projected_rows": rows,
        "partition_count": partitions,
        "projected_row_groups": row_groups,
        "bytes_per_row": int(measured["bytes_per_row"]),
        "footer_per_row_group_bytes": footer_per_row_group,
        "framing_per_file_bytes": framing_per_file,
        "projected_payload_bytes": payload,
        "projected_overhead_bytes": overhead,
        "projected_bytes": payload + overhead,
        "largest_partition_bytes": largest,
        "schema": list(measured["schema"]),
        "witness_measured_rows": int(measured["measured_rows"]),
        "witness_file_bytes": int(measured["file_bytes"]),
    }


def partition_row_counts(
    rows: Sequence[Mapping[str, Any]], *, fields: Sequence[str]
) -> tuple[int, ...]:
    counts: dict[tuple[str, ...], int] = {}
    for row in rows:
        key = tuple(str(row[field]) for field in fields)
        counts[key] = counts.get(key, 0) + 1
    return tuple(counts[key] for key in sorted(counts))


def verify_retained_sample(
    sample: CohortSample,
    *,
    sample_dir: Path,
    sidecar_dir: Path,
    checkpoint: Mapping[str, Any],
) -> tuple[bytes, str]:
    """Re-prove one retained object completely, and report its accepted schema kind."""
    context = {"key": sample.key}
    entry = checkpoint.get(sample.key)
    _require(isinstance(entry, dict), "the cohort sample has no checkpoint evidence", context)
    assert isinstance(entry, dict)
    _exact(
        str(entry.get("status") or ""), "complete", field_name="checkpoint.status", context=context
    )
    _exact(
        entry.get("checksum_match"), True, field_name="checkpoint.checksum_match", context=context
    )
    _exact(str(entry.get("url") or ""), sample.url, field_name="checkpoint.url", context=context)
    digest = str(entry.get("sha256") or "")
    blob = Path(sample_dir) / digest
    _require(
        blob.is_file(), "the retained sample bytes are missing", {**context, "sha256": digest}
    )
    actual = compute_sha256(blob)
    _require(
        actual == digest and blob.name == actual,
        "the retained sample does not match its content address",
        {**context, "expected": digest, "actual": actual},
    )
    payload = blob.read_bytes()
    _exact(
        int(entry.get("byte_size") or 0),
        len(payload),
        field_name="checkpoint.byte_size",
        context=context,
    )
    verify_provider_sidecar(
        key=sample.key,
        object_sha256=actual,
        sidecar_path=Path(str(entry.get("provider_checksum_path") or "")),
        sidecar_sha256=str(entry.get("provider_checksum_sha256") or ""),
        sidecar_dir=Path(sidecar_dir),
    )
    schema_kind = str(entry.get("schema_kind") or "")
    _require(
        schema_kind in {"headed", "headerless"},
        "the retained sample has no accepted schema kind",
        {**context, "schema_kind": schema_kind},
    )
    _require(
        bool(entry.get("schema_fields")),
        "the retained sample has no accepted schema fields",
        context,
    )
    return payload, schema_kind


# --- projection ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProductProjection:
    """One required product's exact partition-by-partition typed storage bound."""

    product: str
    component: str
    components: tuple[Mapping[str, Any], ...]
    partition_count: int
    projected_rows: int
    projected_row_groups: int
    projected_payload_bytes: int
    projected_overhead_bytes: int
    projected_manifest_bytes: int
    projected_target_only_bytes: int
    partition_rows: tuple[int, ...]
    projected_bytes: int
    largest_partition_bytes: int
    input_objects: int
    input_compressed_bytes: int
    manifest_mappings: int
    partitions: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_product": self.product,
            "component": self.component,
            "components": [dict(item) for item in self.components],
            "partition_count": self.partition_count,
            "projected_rows": self.projected_rows,
            "projected_row_groups": self.projected_row_groups,
            "projected_payload_bytes": self.projected_payload_bytes,
            "projected_overhead_bytes": self.projected_overhead_bytes,
            "projected_partition_manifest_bytes": self.projected_manifest_bytes,
            "projected_target_only_bytes": self.projected_target_only_bytes,
            "partition_expected_rows": list(self.partition_rows),
            "projected_bytes": self.projected_bytes,
            "largest_partition_bytes": self.largest_partition_bytes,
            "input_objects": self.input_objects,
            "input_compressed_bytes": self.input_compressed_bytes,
            "partition_manifest_mappings": self.manifest_mappings,
            "partitions": [dict(item) for item in self.partitions],
            "byte_equation": (
                "per partition: sum over components of "
                "ceil(component_bytes * payload_num / payload_den), plus "
                "row_groups * footer_per_row_group, plus framing, plus the partition "
                "manifest mapping bytes for every contributing raw object"
            ),
            "ratio_selection": "greatest exact rational by cross multiplication",
        }


_CADENCE_SPAN_SECONDS: Mapping[str, int] = {"daily": 86_400, "monthly": 31 * 86_400}


def family_cadence_seconds(family: str) -> int:
    """The accepted fixed cadence of a family, or zero when it is event-driven.

    An unlisted family blocks. A fixed-cadence product never silently degrades into an
    observed-ratio-only bound because its archive key carries no interval segment.
    """
    if family in FAMILY_CADENCE_SECONDS:
        return int(FAMILY_CADENCE_SECONDS[family])
    _require(
        family in EVENT_DRIVEN_FAMILIES,
        "a physical family has no accepted cadence declaration",
        {"family": family},
    )
    return 0


def calendar_row_bound(objects: Sequence[PhysicalObject]) -> int:
    """The declared cadence/calendar maximum row count for one partition group."""
    total = 0
    for item in objects:
        seconds = family_cadence_seconds(item.family)
        if seconds <= 0:
            return 0
        cadence = item.family.partition("/")[0]
        span = _CADENCE_SPAN_SECONDS.get(cadence, 0)
        _require(
            span > 0,
            "a physical family has no accepted archive cadence span",
            {"family": item.family},
        )
        total += ceil_div(span, seconds)
    return total


def typed_coefficients(
    measurements: Sequence[TypedEnvelopeMeasurement],
) -> dict[str, dict[str, Any]]:
    """Per product contribution: the greatest observed exact payload and row rationals."""
    best: dict[str, dict[str, Any]] = {}
    for item in measurements:
        context = {"key": item.key, "contribution": item.contribution}
        payload = _positive_int(
            item.payload_bytes, field_name="typed_payload_bytes", context=context
        )
        compressed = _positive_int(
            item.compressed_archive_bytes,
            field_name="compressed_archive_bytes",
            context=context,
        )
        rows = _positive_int(item.rows, field_name="rows", context=context)
        current = best.get(item.contribution)
        if current is None:
            best[item.contribution] = {
                "payload": (payload, compressed, item.key),
                "rows": (rows, compressed, item.key),
                "footer_per_row_group": item.footer_per_row_group(),
                "framing": item.framing_bytes,
                "samples": 1,
                "family": item.family,
                "product": item.product,
            }
            continue
        current["samples"] += 1
        current["footer_per_row_group"] = max(
            int(current["footer_per_row_group"]), item.footer_per_row_group()
        )
        current["framing"] = max(int(current["framing"]), item.framing_bytes)
        if ratio_exceeds(
            (payload, compressed), (current["payload"][0], current["payload"][1])
        ):
            current["payload"] = (payload, compressed, item.key)
        if ratio_exceeds((rows, compressed), (current["rows"][0], current["rows"][1])):
            current["rows"] = (rows, compressed, item.key)
    return best


def group_objects(
    objects: Sequence[PhysicalObject],
) -> dict[tuple[str, str, str], list[PhysicalObject]]:
    """Exact required-product / symbol / UTC-month partitions: one file per group.

    Daily and monthly packaging of one product land in the same partition. A raw object
    that feeds two products appears in both product partitions.
    """
    groups: dict[tuple[str, str, str], list[PhysicalObject]] = {}
    for item in objects:
        for contribution_item in contributions_for_family(item.family):
            key = (
                contribution_item.product,
                item.symbol,
                utc_month(item.economic_interval),
            )
            groups.setdefault(key, []).append(item)
    return groups


def project_typed_partitions(
    *,
    measurements: Sequence[TypedEnvelopeMeasurement],
    objects: Sequence[PhysicalObject],
    lineage: LineageManifestModel,
    target_only_bytes_per_row: Mapping[str, int] | None = None,
) -> tuple[ProductProjection, ...]:
    """Project every archive-fed required product partition by partition."""
    coefficients = typed_coefficients(measurements)
    projections: list[ProductProjection] = []
    work: list[tuple[str, str, tuple[ProductContribution, ...]]] = []
    for product in REQUIRED_PRODUCTS:
        items = contributions_for_product(product)
        if product == PRODUCT_COST_CALIBRATION:
            for item in items:
                component = {
                    "daily_book_ticker": "retained_book_ticker",
                    "daily_book_depth": "retained_book_depth",
                }[item.component]
                work.append((product, component, (item,)))
        elif items:
            work.append((product, "target_product", items))
    for product, projection_component, items in work:
        context = {"required_product": product}
        for item in items:
            _require(
                item.name in coefficients,
                "a required product contribution has no measured coefficient",
                {**context, "contribution": item.name},
            )
        by_family = {item.family: coefficients[item.name] for item in items}
        footer_per_row_group = max(
            int(value["footer_per_row_group"]) for value in by_family.values()
        )
        framing = max(int(value["framing"]) for value in by_family.values())
        rates = dict(target_only_bytes_per_row or {})
        target_rate = int(
            rates.get(f"{product}:{projection_component}", rates.get(product, 0))
        )
        partitions: dict[tuple[str, str], list[PhysicalObject]] = {}
        for source in objects:
            if source.family not in by_family:
                continue
            partitions.setdefault(
                (source.symbol, utc_month(source.economic_interval)), []
            ).append(source)
        _require(
            bool(partitions),
            "a required product has no grouped input bytes",
            context,
        )
        total = 0
        payload_total = 0
        overhead_total = 0
        manifest_total = 0
        target_total = 0
        partition_rows: list[int] = []
        partition_descriptors: list[Mapping[str, Any]] = []
        rows_total = 0
        row_groups_total = 0
        largest = 0
        mappings = 0
        calendar_bounded = False
        observed_bounded = False
        for members in partitions.values():
            payload_bytes = 0
            row_candidates: list[int] = []
            for family, family_members in _by_family(members).items():
                coefficient = by_family[family]
                family_bytes = sum(int(row.byte_size) for row in family_members)
                _require(
                    family_bytes > 0, "a partition component has no input bytes", context
                )
                payload_bytes += ceil_div(
                    family_bytes * coefficient["payload"][0],
                    coefficient["payload"][1],
                )
                observed_rows = ceil_div(
                    family_bytes * coefficient["rows"][0], coefficient["rows"][1]
                )
                calendar_rows = calendar_row_bound(family_members)
                if calendar_rows > 0:
                    calendar_bounded = True
                else:
                    observed_bounded = True
                # ADR-0024: the greater applicable bound wins.
                row_candidates.append(max(observed_rows, calendar_rows))
            # Every target product publishes one causally aligned output grid per
            # native/month partition. Physical input bytes still sum, but the daily,
            # monthly, mark, index, and premium input ceilings never become extra rows.
            rows = max(row_candidates)
            row_groups = max(1, ceil_div(rows, SIZING_ROW_BATCH))
            # Target-only fields are published by this product and by no contribution.
            payload_bytes += rows * target_rate
            # Every contributing raw object is mapped in this partition's own lineage
            # manifest, which carries its own row-group metadata and framing.
            manifest_mappings = len(members)
            local = lineage.partition_bytes(manifest_mappings, kind="archive")
            manifest_charge = int(local["bytes"])
            overhead = row_groups * footer_per_row_group + framing
            file_bytes = payload_bytes + overhead + manifest_charge
            payload_total += payload_bytes
            overhead_total += overhead
            manifest_total += manifest_charge
            target_total += rows * target_rate
            mappings += manifest_mappings
            rows_total += rows
            partition_rows.append(rows)
            first = members[0]
            partition_descriptors.append(
                {
                    "required_product": product,
                    "component": projection_component,
                    "native_symbol": first.symbol,
                    "utc_month": utc_month(first.economic_interval),
                    "expected_rows": rows,
                    "mappings": manifest_mappings,
                }
            )
            row_groups_total += row_groups
            total += file_bytes
            largest = max(largest, file_bytes)
        components = tuple(
            {
                "contribution": item.name,
                "component": item.component,
                "physical_family": item.family,
                "payload_ratio_numerator_typed_bytes": by_family[item.family]["payload"][0],
                "payload_ratio_denominator_compressed_bytes": (
                    by_family[item.family]["payload"][1]
                ),
                "payload_ratio_witness_key": by_family[item.family]["payload"][2],
                "row_ratio_numerator_rows": by_family[item.family]["rows"][0],
                "row_ratio_denominator_compressed_bytes": by_family[item.family]["rows"][1],
                "row_ratio_witness_key": by_family[item.family]["rows"][2],
                "sample_count": by_family[item.family]["samples"],
                "cadence_seconds": family_cadence_seconds(item.family),
                "row_bound_source": (
                    "declared cadence calendar maximum"
                    if family_cadence_seconds(item.family) > 0
                    else "greatest observed exact row-to-compressed ratio"
                ),
                "footer_per_row_group_bytes": by_family[item.family][
                    "footer_per_row_group"
                ],
                "framing_bytes_per_file": by_family[item.family]["framing"],
            }
            for item in items
        )
        projections.append(
            ProductProjection(
                product=product,
                component=projection_component,
                components=components,
                partition_count=len(partitions),
                projected_rows=rows_total,
                projected_row_groups=row_groups_total,
                projected_payload_bytes=payload_total,
                projected_overhead_bytes=overhead_total,
                projected_manifest_bytes=manifest_total,
                projected_target_only_bytes=target_total,
                partition_rows=tuple(partition_rows),
                projected_bytes=total,
                largest_partition_bytes=largest,
                input_objects=sum(len(value) for value in partitions.values()),
                input_compressed_bytes=sum(
                    sum(int(row.byte_size) for row in value)
                    for value in partitions.values()
                ),
                manifest_mappings=mappings,
                partitions=tuple(partition_descriptors),
            )
        )
        _require(
            calendar_bounded or observed_bounded,
            "a required product bounded no rows at all",
            context,
        )
    return tuple(projections)


def _by_family(
    members: Sequence[PhysicalObject],
) -> dict[str, list[PhysicalObject]]:
    grouped: dict[str, list[PhysicalObject]] = {}
    for item in members:
        grouped.setdefault(item.family, []).append(item)
    return grouped


# --- Coinalyze authority, evidence, and projection --------------------------------------


@dataclass(frozen=True, slots=True)
class CoinalyzeEvidence:
    """One accepted retained Coinalyze response, re-proved from the report's provenance."""

    endpoint: str
    role: str
    sha256: str
    byte_size: int
    content_path: str
    payload: bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "role": self.role,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "content_path": self.content_path,
        }


def _normalized_parameter_name(name: str) -> str:
    return name.lower().replace("_", "").replace("-", "")


def prove_coinalyze_request_framing(block: Mapping[str, Any]) -> dict[str, Any]:
    """Prove the accepted report frames Coinalyze as header authentication only.

    The accepted qualification sends its key as a request header and publishes only that
    header's name. This proves the framing itself before any provenance record is read,
    so a report that ever moved the key into a query string blocks here.
    """
    context = {"source": "report.coinalyze"}
    _require(
        str(block.get("key_location") or "") == "header",
        "the accepted Coinalyze framing is not header authentication",
        {**context, "field": "key_location"},
    )
    _require(
        block.get("key_present") is True,
        "the accepted Coinalyze framing does not declare a present key",
        {**context, "field": "key_present"},
    )
    _require(
        block.get("query_contains_key") is False,
        "the accepted Coinalyze framing does not exclude query credentials",
        {**context, "field": "query_contains_key"},
    )
    return {
        "key_location": "header",
        "key_present": True,
        "query_contains_key": False,
    }


def prove_coinalyze_provenance_record(
    record: Mapping[str, Any], *, endpoint: str, context: Mapping[str, Any]
) -> None:
    """Prove one provenance record carries the accepted safe shape and nothing else.

    Only field names, structural types, and the endpoint reach the failure surface. No
    rejected value and no serialized record is ever placed in a message or a context, so
    a report that did carry a secret could not leak it through this failure path.
    """
    local = {**dict(context), "endpoint": endpoint}
    fields = set(record)
    unknown = sorted(fields - ACCEPTED_COINALYZE_PROVENANCE_FIELDS)
    _require(
        not unknown,
        "a Coinalyze provenance record carries an unrecognized field",
        {**local, "unexpected_fields": unknown[:8]},
    )
    missing = sorted(ACCEPTED_COINALYZE_PROVENANCE_FIELDS - fields)
    _require(
        not missing,
        "a Coinalyze provenance record is missing an accepted field",
        {**local, "missing_fields": missing[:8]},
    )
    header_names = record.get("header_names")
    _require(
        isinstance(header_names, list)
        and all(isinstance(item, str) for item in header_names)
        and tuple(header_names) == ACCEPTED_COINALYZE_HEADER_NAMES,
        "a Coinalyze provenance record does not declare the accepted header names",
        {**local, "field": "header_names"},
    )
    params = record.get("params")
    _require(
        isinstance(params, dict)
        and all(
            isinstance(name, str) and isinstance(value, str)
            for name, value in params.items()
        ),
        "a Coinalyze provenance record has a non string-to-string parameter map",
        {**local, "field": "params"},
    )
    offending = sorted(
        name
        for name in params
        if any(
            marker in _normalized_parameter_name(name)
            for marker in CREDENTIAL_PARAMETER_MARKERS
        )
    )
    _require(
        not offending,
        "a Coinalyze provenance record names a credential query parameter",
        # The parameter name is structural; its value is never read or reported.
        {**local, "field": "params", "parameter_names": offending[:8]},
    )


def _endpoint_role(endpoint: str) -> str:
    if endpoint == COINALYZE_MARKETS_ENDPOINT:
        return "future_market_inventory"
    if endpoint == COINALYZE_LIQUIDATION_ENDPOINT:
        return "liquidation_charge_witness"
    if endpoint in COINALYZE_OVERLAP_ENDPOINTS:
        return "bounded_overlap_evidence"
    return ""


def resolve_coinalyze_evidence(
    authority: SizingAuthority, *, cache_dir: Path
) -> tuple[CoinalyzeEvidence, ...]:
    """The exact five accepted responses, path-confined, size-checked, and rehashed.

    Every identity comes from the report's own provenance. The cache is content-addressed
    and carries no file extension, so responses are found by their recorded content path
    rather than by globbing, and each endpoint keeps its own role.

    The accepted key travels only as a request header, and the report publishes only that
    header's *name*. A header name is metadata and is proved against the accepted value;
    a header value, a credential query parameter under any spelling, and any field
    outside the accepted shape all block before a response body is read.
    """
    context = {"cache_dir": str(cache_dir)}
    block = dict(authority.report.get("coinalyze") or {})
    prove_coinalyze_request_framing(block)
    provenance = list(block.get("provenance") or ())
    _exact(
        len(provenance),
        ACCEPTED_COINALYZE_PROVENANCE_RECORDS,
        field_name="coinalyze_provenance_records",
        context=context,
    )
    resolved_root = Path(cache_dir).resolve()
    evidence: list[CoinalyzeEvidence] = []
    for record in provenance:
        _require(
            isinstance(record, dict),
            "a Coinalyze provenance record is not an object",
            context,
        )
        endpoint = str(record.get("path") or "")
        role = _endpoint_role(endpoint)
        _require(
            bool(role),
            "a Coinalyze provenance record names an unknown endpoint",
            {**context, "endpoint": endpoint},
        )
        prove_coinalyze_provenance_record(record, endpoint=endpoint, context=context)
        content_path = Path(str(record.get("content_path") or ""))
        _require(
            content_path.is_file(),
            "an accepted Coinalyze response body is missing",
            {**context, "endpoint": endpoint, "path": str(content_path)},
        )
        resolved = content_path.resolve()
        _require(
            resolved.parent == resolved_root and not content_path.is_symlink(),
            "an accepted Coinalyze response escapes its cache",
            {**context, "path": str(content_path)},
        )
        digest = str(record.get("sha256") or "")
        payload = content_path.read_bytes()
        _exact(
            _sha256_bytes(payload),
            digest,
            field_name=f"coinalyze_response_sha256[{endpoint}]",
            context=context,
        )
        _exact(
            len(payload),
            int(record.get("byte_size") or -1),
            field_name=f"coinalyze_response_bytes[{endpoint}]",
            context=context,
        )
        _exact(
            resolved.name,
            digest,
            field_name=f"coinalyze_response_content_address[{endpoint}]",
            context=context,
        )
        evidence.append(
            CoinalyzeEvidence(
                endpoint=endpoint,
                role=role,
                sha256=digest,
                byte_size=len(payload),
                content_path=str(content_path),
                payload=payload,
            )
        )
    roles = [item.role for item in evidence]
    _exact(
        roles.count("liquidation_charge_witness"),
        1,
        field_name="coinalyze_liquidation_witnesses",
        context=context,
    )
    _exact(
        roles.count("future_market_inventory"),
        1,
        field_name="coinalyze_inventory_records",
        context=context,
    )
    return tuple(evidence)


@dataclass(frozen=True, slots=True)
class CoinalyzeIdentityMap:
    """The proved one-to-one Coinalyze-provider / Binance-native identity bindings.

    Coinalyze names a Binance perpetual twice: its own provider identity (``symbol``,
    for example ``BTCUSDT_PERP.A``) and the venue's native identity
    (``symbol_on_exchange``, for example ``BTCUSDT``). The two namespaces are never
    interchangeable and neither is ever derived from the other by editing a string. The
    pinned future-market inventory is the only authority that binds them.
    """

    provider_to_native: Mapping[str, str]
    native_to_provider: Mapping[str, str]
    perpetual_markets: int

    def native_for(self, provider: str, *, context: Mapping[str, Any]) -> str:
        native = self.provider_to_native.get(provider)
        _require(
            native is not None,
            "a Coinalyze provider identity is absent from the accepted inventory",
            {**dict(context), "provider_symbol": provider},
        )
        assert native is not None
        return native

    def provider_for(self, native: str, *, context: Mapping[str, Any]) -> str:
        provider = self.native_to_provider.get(native)
        _require(
            provider is not None,
            "a Binance native identity is absent from the accepted inventory",
            {**dict(context), "native_symbol": native},
        )
        assert provider is not None
        return provider

    def to_dict(self) -> dict[str, Any]:
        return {
            "binance_perpetual_markets": self.perpetual_markets,
            "identity_source": "future-markets.symbol / future-markets.symbol_on_exchange",
            "derivation": "none; the retained provider/native pair is the only authority",
        }


def prove_coinalyze_identity_map(
    authority: SizingAuthority, *, inventory: CoinalyzeEvidence
) -> CoinalyzeIdentityMap:
    """Bind every retained Binance perpetual market to its native identity, exactly once.

    Only rows the inventory itself marks as Binance perpetuals participate; the other
    retained identities are real evidence for other venues and instruments and are never
    counted in this projection. A missing field, a wrong type, a repeated market, a
    provider bound to two natives, or a native bound to two providers all block.
    """
    context = {"endpoint": inventory.endpoint}
    try:
        markets = json.loads(inventory.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SizingError(
            "the accepted future-market inventory is not JSON", context=context
        ) from exc
    _require(
        isinstance(markets, list) and bool(markets),
        "the accepted future-market inventory carries no market",
        context,
    )
    provider_to_native: dict[str, str] = {}
    native_to_provider: dict[str, str] = {}
    for row in markets:
        if not isinstance(row, dict):
            continue
        exchange = row.get("exchange")
        if not isinstance(exchange, str) or exchange != COINALYZE_EXCHANGE_CODE:
            continue
        perpetual = row.get("is_perpetual")
        _require(
            isinstance(perpetual, bool),
            "a Binance inventory row does not declare is_perpetual as a boolean",
            {**context, "field": "is_perpetual"},
        )
        if not perpetual:
            continue
        provider_value = row.get("symbol")
        native_value = row.get("symbol_on_exchange")
        _require(
            isinstance(provider_value, str) and bool(provider_value.strip()),
            "a Binance perpetual inventory row has no provider symbol",
            {**context, "field": "symbol"},
        )
        _require(
            isinstance(native_value, str) and bool(native_value.strip()),
            "a Binance perpetual inventory row has no symbol_on_exchange",
            {**context, "field": "symbol_on_exchange"},
        )
        provider = str(provider_value).strip()
        native = str(native_value).strip().upper()
        bound_native = provider_to_native.get(provider)
        bound_provider = native_to_provider.get(native)
        _require(
            bound_native is None or bound_native == native,
            "a Coinalyze provider identity binds two native identities",
            {**context, "provider_symbol": provider},
        )
        _require(
            bound_provider is None or bound_provider == provider,
            "a Binance native identity binds two Coinalyze provider identities",
            {**context, "native_symbol": native},
        )
        _require(
            bound_native is None and bound_provider is None,
            "the accepted inventory repeats a Binance perpetual market",
            {**context, "native_symbol": native},
        )
        provider_to_native[provider] = native
        native_to_provider[native] = provider
    _require(
        bool(provider_to_native),
        "the accepted inventory carries no Binance perpetual market",
        context,
    )
    _exact(
        len(native_to_provider),
        len(provider_to_native),
        field_name="coinalyze_identity_map_is_one_to_one",
        context=context,
    )
    block = dict(authority.report.get("coinalyze") or {})
    for field in ("binance_perpetual_market_count", "native_identity_validated_markets"):
        declared = block.get(field)
        _require(
            isinstance(declared, int) and not isinstance(declared, bool) and declared > 0,
            "the accepted report does not declare a positive inventory market count",
            {**context, "field": field},
        )
        _exact(
            int(declared),
            len(provider_to_native),
            field_name=f"coinalyze.{field}",
            context=context,
        )
    return CoinalyzeIdentityMap(
        provider_to_native=dict(provider_to_native),
        native_to_provider=dict(native_to_provider),
        perpetual_markets=len(provider_to_native),
    )


def prove_coinalyze_anchor_identity(
    authority: SizingAuthority,
    *,
    identities: CoinalyzeIdentityMap,
    retained_provider_symbols: Sequence[str],
) -> dict[str, Any]:
    """Re-prove every accepted anchor triple against the inventory and the real response.

    The report records each anchor three ways: its native symbol, the inventory's
    ``symbol_on_exchange``, and the Coinalyze provider symbol. All three must agree with
    each other, with the proved inventory mapping, with the requested and matched market
    lists, and with the provider identities the retained liquidation response carries.
    """
    context = {"source": "report.coinalyze.anchor_identity"}
    block = dict(authority.report.get("coinalyze") or {})
    rows = list(block.get("anchor_identity") or ())
    _require(bool(rows), "the accepted report declares no anchor identity", context)
    natives: list[str] = []
    providers: list[str] = []
    for row in rows:
        _require(isinstance(row, dict), "an anchor identity row is not an object", context)
        native = str(dict(row).get("native_symbol") or "")
        on_exchange = str(dict(row).get("symbol_on_exchange") or "")
        provider = str(dict(row).get("provider_symbol") or "")
        _require(
            bool(native) and bool(on_exchange) and bool(provider),
            "an anchor identity row is missing one of its three identities",
            context,
        )
        _exact(
            on_exchange.strip().upper(),
            native.strip().upper(),
            field_name="anchor_identity.symbol_on_exchange",
            context={**context, "native_symbol": native},
        )
        _exact(
            identities.native_for(provider, context=context),
            native.strip().upper(),
            field_name="anchor_identity.provider_to_native",
            context={**context, "provider_symbol": provider},
        )
        _exact(
            identities.provider_for(native.strip().upper(), context=context),
            provider,
            field_name="anchor_identity.native_to_provider",
            context={**context, "native_symbol": native},
        )
        natives.append(native.strip().upper())
        providers.append(provider)
    _require(
        len(set(natives)) == len(natives) and len(set(providers)) == len(providers),
        "the accepted report repeats an anchor identity",
        context,
    )
    declared_anchors = {
        str(item).strip().upper() for item in (block.get("anchor_symbols") or ())
    }
    _require(
        declared_anchors == set(natives),
        "the accepted anchor symbols disagree with the anchor identity rows",
        {**context, "field": "anchor_symbols"},
    )
    requested = {str(item) for item in (block.get("requested_symbols") or ())}
    _require(
        requested == set(providers),
        "the accepted requested symbols disagree with the anchor provider identities",
        {**context, "field": "requested_symbols"},
    )
    matched = {str(item) for item in (block.get("matched_markets") or ())}
    _require(
        matched == set(providers),
        "the accepted matched markets disagree with the anchor provider identities",
        {**context, "field": "matched_markets"},
    )
    retained = {str(item) for item in retained_provider_symbols}
    _require(
        retained == set(providers),
        "the retained liquidation response disagrees with the accepted anchors",
        {**context, "field": "retained_provider_symbols"},
    )
    return {
        "anchor_native_symbols": sorted(natives),
        "anchor_provider_symbols": sorted(providers),
        "retained_provider_symbols": sorted(retained),
    }


def coinalyze_symbol_sets(
    authority: SizingAuthority,
    *,
    inventory: CoinalyzeEvidence,
    identities: CoinalyzeIdentityMap,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The complete accepted supported and unmapped symbol sets, in native identity.

    Supported mappings and typed gaps are Binance-native identities. Each supported one
    must have exactly one proved inventory binding; a provider label, a base asset, or
    any other inventory string is never accepted as interchangeable evidence for it.
    """
    context = {"endpoint": inventory.endpoint}
    block = dict(authority.report.get("coinalyze") or {})
    support = dict(block.get("universe_support") or {})
    supported = tuple(str(item) for item in (support.get("supported_symbols") or ()))
    unmapped = tuple(str(item) for item in (support.get("unmapped_symbols") or ()))
    _exact(
        len(supported),
        ACCEPTED_COINALYZE_SUPPORTED_MAPPINGS,
        field_name="coinalyze_supported_count",
        context=context,
    )
    _exact(
        len(unmapped),
        ACCEPTED_COINALYZE_TYPED_GAPS,
        field_name="coinalyze_typed_gaps",
        context=context,
    )
    _exact(
        int(support.get("supported_count") or -1),
        len(supported),
        field_name="coinalyze_supported_count_field",
        context=context,
    )
    _exact(
        int(support.get("unmapped_count") or -1),
        len(unmapped),
        field_name="coinalyze_unmapped_count_field",
        context=context,
    )
    _require(
        not (set(supported) & set(unmapped)),
        "a Coinalyze symbol is both supported and unmapped",
        context,
    )
    # Each supported native mapping must have exactly one proved inventory binding.
    missing_inventory = sorted(
        symbol for symbol in supported if symbol not in identities.native_to_provider
    )
    _require(
        not missing_inventory,
        "a supported Coinalyze mapping has no proved native inventory binding",
        {**context, "symbols": missing_inventory[:8]},
    )
    _require(
        len({identities.native_to_provider[symbol] for symbol in supported})
        == len(set(supported)),
        "two supported native mappings share one Coinalyze provider identity",
        context,
    )
    # The inventory legitimately carries identities outside this projection. They are
    # never counted here and never expand the supported set.
    _require(
        len(set(supported)) <= identities.perpetual_markets,
        "the supported set exceeds the proved Binance perpetual inventory",
        {**context, "supported": len(set(supported))},
    )
    membership = dict(authority.report.get("membership") or {})
    accepted_universe = {
        str(item.get("symbol"))
        for item in (membership.get("classifications") or ())
        if isinstance(item, dict) and item.get("accepted") is True
    }
    if accepted_universe:
        unknown = sorted(
            symbol
            for symbol in unmapped
            if symbol not in accepted_universe
        )
        _require(
            not unknown,
            "an unmapped Coinalyze gap names a symbol outside accepted membership",
            {**context, "symbols": unknown[:8]},
        )
    return tuple(sorted(supported)), tuple(sorted(unmapped))


def coinalyze_lifecycles(
    authority: SizingAuthority, *, supported: Sequence[str]
) -> tuple[dict[str, tuple[int, int]], str]:
    """Authenticated lifecycle day bounds per supported mapping, through the cutoff.

    Bounds come only from the accepted report's membership evidence and the pinned
    official metadata, both keyed by Binance-native identity. A supported mapping without
    authenticated bounds blocks; it never receives zero days and never accepts caller
    data, and no native identity is ever reconstructed from a provider string.
    """
    cutoff = str(authority.report.get("generated_at") or "")
    _require(bool(cutoff), "the accepted report has no qualification cutoff", {})
    cutoff_day = _utc_day(cutoff, field_name="cutoff")
    snapshot = dict(authority.contract_metadata.get("symbol_snapshot") or {})
    membership = dict(authority.report.get("membership") or {})
    rows = {
        str(item.get("symbol")): item
        for item in (membership.get("classifications") or ())
        if isinstance(item, dict)
    }
    lifecycles: dict[str, tuple[int, int]] = {}
    unknown: list[str] = []
    for symbol in supported:
        # `supported` is Binance-native identity, and so are the official metadata
        # snapshot and the membership classifications. Nothing is derived from a string.
        # The pinned contract file maps a symbol to a snapshot digest, so it proves the
        # contract was retained; the lifecycle bounds come from the accepted evidence.
        onboard: Any = None
        close: Any = None
        evidence = rows.get(symbol) or {}
        records = (
            list(evidence.get("evidence") or ()) if isinstance(evidence, dict) else []
        )
        for item in records:
            if not isinstance(item, dict) or item.get("onboard_ms") is None:
                continue
            onboard = item.get("onboard_ms")
            close = item.get("closed_observed_ms")
            if close is None:
                close = item.get("delivery_ms")
            break
        _require(
            symbol in snapshot,
            "a supported mapping has no retained contract snapshot",
            {"symbol": symbol},
        )
        if not isinstance(onboard, int) or isinstance(onboard, bool) or onboard <= 0:
            unknown.append(symbol)
            continue
        first = _utc_day_from_ms(onboard)
        last = cutoff_day
        if isinstance(close, int) and not isinstance(close, bool) and 0 < close:
            last = min(last, _utc_day_from_ms(close))
        if last < first:
            unknown.append(symbol)
            continue
        lifecycles[symbol] = (first, last)
    _require(
        not unknown,
        "a supported Coinalyze mapping has no authenticated lifecycle",
        {"symbols": unknown[:8], "unknown_count": len(unknown)},
    )
    return lifecycles, cutoff


def _utc_day(value: str, *, field_name: str) -> int:
    text = str(value).strip()
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00").replace(" ", "T"))
    except ValueError as exc:
        raise SizingError(
            "a lifecycle bound is not an ISO UTC instant",
            context={"field": field_name, "value": text},
        ) from exc
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).date().toordinal()


def _utc_day_from_ms(value: int) -> int:
    """Integer epoch conversion. Milliseconds never become a float on this path."""
    seconds = int(value) // 1000
    return datetime.fromtimestamp(seconds, UTC).date().toordinal()


def _utc_month_of_day(day: int) -> str:
    return datetime.fromordinal(day).strftime("%Y-%m")


@dataclass(frozen=True, slots=True)
class CoinalyzeProjection:
    """Bounded liquidation projection from real charges, lifecycles, and envelopes."""

    supported_mappings: int
    typed_gaps: int
    point_charge_bytes: int
    framing_charge_bytes: int
    projected_points: int
    gross_required_raw_bytes: int
    gross_inventory_bytes: int
    gross_liquidation_bytes: int
    retained_receipts: int
    retained_raw_bytes: int
    retained_inventory_receipts: int
    retained_inventory_bytes: int
    retained_liquidation_receipts: int
    retained_liquidation_bytes: int
    retained_provider_symbols: tuple[str, ...]
    retained_native_symbols: tuple[str, ...]
    retained_points: int
    retained_partitions: tuple[tuple[str, str], ...]
    projected_new_raw_bytes: int
    inventory_receipts: int
    liquidation_receipts: int
    overlap_evidence_receipts: int
    envelope_numerator: int
    envelope_denominator: int
    envelope_witness: str
    projected_normalized_bytes: int
    projected_typed_payload_bytes: int
    projected_typed_overhead_bytes: int
    projected_manifest_bytes: int
    manifest_mappings: int
    partition_count: int
    largest_partition_bytes: int
    evidence: tuple[Mapping[str, Any], ...]
    envelopes: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "supported_mappings": self.supported_mappings,
            "typed_unsupported_gaps": self.typed_gaps,
            "greatest_point_charge_bytes": self.point_charge_bytes,
            "greatest_response_framing_bytes": self.framing_charge_bytes,
            "request_framing": "one symbol per request; no unproved batching credit",
            "semantics": "observed and censored liquidation aggregate, never complete",
            "projected_points": self.projected_points,
            "gross_required_raw_bytes": self.gross_required_raw_bytes,
            "gross_inventory_bytes": self.gross_inventory_bytes,
            "gross_liquidation_bytes": self.gross_liquidation_bytes,
            "retained_receipts": self.retained_receipts,
            "retained_raw_bytes": self.retained_raw_bytes,
            "retained_inventory_receipts": self.retained_inventory_receipts,
            "retained_inventory_bytes": self.retained_inventory_bytes,
            "retained_liquidation_receipts": self.retained_liquidation_receipts,
            "retained_liquidation_bytes": self.retained_liquidation_bytes,
            "retained_covered_symbols": len(self.retained_native_symbols),
            "retained_provider_symbols": list(self.retained_provider_symbols),
            "retained_native_symbols": list(self.retained_native_symbols),
            "identity_namespaces": (
                "supported mappings, lifecycles, projection groups, and partition keys "
                "are Binance-native; retained API series are Coinalyze provider identity"
            ),
            "retained_points": self.retained_points,
            "retained_partitions": [
                {"native_symbol": symbol, "utc_month": month}
                for symbol, month in self.retained_partitions
            ],
            "projected_new_raw_bytes": self.projected_new_raw_bytes,
            "inventory_receipts": self.inventory_receipts,
            "liquidation_receipts": self.liquidation_receipts,
            "overlap_evidence_receipts": self.overlap_evidence_receipts,
            "projected_acquisition_receipts": (
                self.inventory_receipts + self.liquidation_receipts
            ),
            "equation": (
                "gross_required_raw_bytes - retained_raw_bytes = projected_new_raw_bytes; "
                "retained coverage is credited by its own proved points and framing, "
                "never by a bare byte subtraction"
            ),
            "normalized_ratio_numerator_parquet_bytes": self.envelope_numerator,
            "normalized_ratio_denominator_raw_bytes": self.envelope_denominator,
            "normalized_ratio_witness": self.envelope_witness,
            "projected_normalized_bytes": self.projected_normalized_bytes,
            "projected_typed_payload_bytes": self.projected_typed_payload_bytes,
            "projected_typed_overhead_bytes": self.projected_typed_overhead_bytes,
            "projected_partition_manifest_bytes": self.projected_manifest_bytes,
            "partition_manifest_mappings": self.manifest_mappings,
            "raw_and_typed_separation": (
                "the raw point charge projects the raw API response receipts; the typed "
                "bytes-per-point coefficient projects normalized payload; neither raw "
                "factor is applied to the other"
            ),
            "partition_count": self.partition_count,
            "largest_partition_bytes": self.largest_partition_bytes,
            "evidence": [dict(item) for item in self.evidence],
            "envelopes": [dict(item) for item in self.envelopes],
        }


def _liquidation_decimal(value: Any, *, field_name: str, context: Mapping[str, Any]) -> Decimal:
    """One retained liquidation lexeme as an exact decimal, never through a float."""
    if isinstance(value, Decimal):
        text = format(value, "f")
    elif isinstance(value, int) and not isinstance(value, bool):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise SizingError(
            "a retained liquidation value is not an exact numeric lexeme",
            context={**dict(context), "field": field_name},
        )
    return convert_decimal(
        text,
        key=str(dict(context).get("endpoint") or ""),
        output=PRODUCT_LIQUIDATION_OBSERVED_DAILY,
        column=field_name,
        row=int(dict(context).get("point_ordinal") or 0),
    )


def measure_liquidation_response(payload: bytes, *, endpoint: str) -> dict[str, Any]:
    """Exact framing and per-point charges from the real retained liquidation response.

    The document is decoded with exact decimal lexemes, so no retained liquidation value
    ever passes through a binary float. Points are kept as typed triples; the retained
    JSON point object is never carried forward as a stored string.
    """
    context = {"endpoint": endpoint}
    try:
        document = json.loads(payload.decode("utf-8"), parse_float=Decimal)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SizingError(
            "the retained liquidation response is not JSON", context=context
        ) from exc
    _require(
        isinstance(document, list) and bool(document),
        "the retained liquidation response is empty",
        context,
    )
    series: list[tuple[str, list[dict[str, Any]]]] = []
    points = 0
    point_bytes = 0
    for row in document:
        _require(isinstance(row, dict), "a liquidation series is not an object", context)
        symbol = str(row.get("symbol") or "")
        history = row.get("history")
        _require(isinstance(history, list), "a liquidation series has no history", context)
        typed: list[dict[str, Any]] = []
        for ordinal, point in enumerate(history):
            _require(isinstance(point, dict), "a liquidation point is not an object", context)
            local = {**context, "point_ordinal": ordinal}
            moment = point.get("t")
            _require(
                isinstance(moment, int) and not isinstance(moment, bool) and moment > 0,
                "a retained liquidation point has no positive timestamp",
                local,
            )
            typed.append(
                {
                    "event_time_ms": int(moment) * 1000,
                    "event_time_seconds": int(moment),
                    "long_liquidation": _liquidation_decimal(
                        point.get("l"), field_name="long_liquidation", context=local
                    ),
                    "short_liquidation": _liquidation_decimal(
                        point.get("s"), field_name="short_liquidation", context=local
                    ),
                }
            )
            # Raw-byte accounting only: this measures the retained API response, never a
            # normalized column. The token is not stored in any typed product.
            point_bytes += len(
                json.dumps(point, sort_keys=True, separators=(",", ":"), default=str).encode(
                    "utf-8"
                )
            )
            points += 1
        series.append((symbol, typed))
    _require(points > 0, "the retained liquidation response carries no point", context)
    return {
        "endpoint": endpoint,
        "response_bytes": len(payload),
        "point_count": points,
        "point_token_bytes": point_bytes,
        "framing_bytes": max(len(payload) - point_bytes, 0),
        "bytes_per_point": ceil_div(point_bytes, points),
        "sha256": _sha256_bytes(payload),
        "series": series,
    }


def write_liquidation_envelope(
    *,
    symbol: str,
    provider_symbol: str,
    endpoint: str,
    points: Sequence[Mapping[str, Any]],
    destination: Path,
    raw_object_ref: int = 0,
) -> dict[str, Any]:
    """One deterministic typed observed-liquidation envelope, measured exactly.

    ``symbol`` is the Binance-native identity and ``provider_symbol`` the Coinalyze one.
    Timestamps are integers and both liquidation values are exact decimals; no JSON point
    object and no repeated identity string is stored per row.
    """
    _require(
        bool(points),
        "a liquidation series has no point to normalize",
        {"native_symbol": symbol, "provider_symbol": provider_symbol},
    )
    identity = native_identity(symbol)
    rows = [
        {
            **identity,
            "raw_object_ref": int(raw_object_ref),
            "point_ordinal": ordinal,
            "provider_symbol": provider_symbol,
            "event_time_ms": int(item["event_time_ms"]),
            "long_liquidation": item["long_liquidation"],
            "short_liquidation": item["short_liquidation"],
            # Positive means the long side dominated the observed aggregate.
            "liquidation_imbalance": _scaled_decimal(
                _unscaled(item["long_liquidation"])
                - _unscaled(item["short_liquidation"])
            ),
            "source_interval_seconds": LIQUIDATION_SOURCE_INTERVAL_SECONDS,
            "observation_semantics": LIQUIDATION_OBSERVATION_LABEL,
            # An observed aggregate is never a complete event record.
            "event_complete": False,
        }
        for ordinal, item in enumerate(points)
    ]
    columns = final_product_columns(PRODUCT_LIQUIDATION_OBSERVED_DAILY)
    table = pa.Table.from_pydict(
        _column_values(columns, rows),
        schema=final_product_schema(PRODUCT_LIQUIDATION_OBSERVED_DAILY),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = pq.ParquetWriter(
        str(destination),
        final_product_schema(PRODUCT_LIQUIDATION_OBSERVED_DAILY),
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
        version=PARQUET_VERSION,
        write_statistics=False,
        store_schema=True,
    )
    try:
        for start_index in range(0, len(points), SIZING_ROW_BATCH):
            writer.write_table(
                table.slice(start_index, SIZING_ROW_BATCH),
                row_group_size=SIZING_ROW_BATCH,
            )
    finally:
        writer.close()
    measured = _measure_parquet_file(destination)
    return {
        **measured,
        "required_product": PRODUCT_LIQUIDATION_OBSERVED_DAILY,
        "native_symbol": symbol,
        "provider_symbol": provider_symbol,
        "endpoint": endpoint,
        "points": len(points),
        "bytes_per_point": ceil_div(measured["payload_bytes"], len(points)),
        "footer_per_row_group_bytes": ceil_div(
            max(measured["footer_bytes"], measured["footer_bytes"] + measured["residual_bytes"]),
            max(measured["row_groups"], 1),
        ),
        "schema": _schema_dict(final_product_schema(PRODUCT_LIQUIDATION_OBSERVED_DAILY)),
        "parquet_sha256": compute_sha256(destination),
        "writer_identity": writer_identity(),
        "pyarrow_version": str(pa.__version__),
    }


def validate_retained_liquidation_coverage(
    measured: Mapping[str, Any],
    *,
    supported: Sequence[str],
    lifecycles: Mapping[str, tuple[int, int]],
    identities: CoinalyzeIdentityMap,
    endpoint: str,
) -> dict[str, Any]:
    """Prove what the retained liquidation response actually covers, before crediting it.

    A retained series names its symbol in Coinalyze provider identity. It is translated
    through the proved inventory binding before anything native is consulted, so an
    unknown provider string, a native string used in a provider position, a repeated
    series, and two provider identities colliding onto one native all block. Every point
    is then parsed: its day must fall inside that native symbol's authenticated
    lifecycle, the query interval must be daily, and a repeated day is never counted
    twice.
    """
    context = {"endpoint": endpoint}
    _exact(
        endpoint,
        COINALYZE_LIQUIDATION_ENDPOINT,
        field_name="retained_liquidation_endpoint",
        context=context,
    )
    supported_set = set(supported)
    providers: list[str] = []
    symbols: list[str] = []
    pairs: list[dict[str, str]] = []
    unique_points = 0
    per_symbol: dict[str, int] = {}
    for provider, typed_points in measured["series"]:
        _require(
            provider not in set(providers),
            "the retained liquidation response repeats a provider series",
            {**context, "provider_symbol": provider},
        )
        symbol = identities.native_for(provider, context=context)
        _require(
            symbol not in set(symbols),
            "two retained provider identities collide onto one native symbol",
            {**context, "native_symbol": symbol},
        )
        _require(
            symbol in supported_set,
            "the retained liquidation response covers an unsupported symbol",
            {**context, "native_symbol": symbol},
        )
        first, last = lifecycles[symbol]
        days: set[int] = set()
        previous: int | None = None
        for point in typed_points:
            moment = int(point["event_time_seconds"])
            _require(
                moment > 0,
                "a retained liquidation point has no positive timestamp",
                {**context, "native_symbol": symbol},
            )
            day = datetime.fromtimestamp(moment, UTC).date().toordinal()
            _require(
                first <= day <= last,
                "a retained liquidation point falls outside its authenticated lifecycle",
                {**context, "native_symbol": symbol},
            )
            if previous is not None:
                _exact(
                    day - previous,
                    1,
                    field_name="retained_liquidation_interval_days",
                    context={**context, "native_symbol": symbol},
                )
            previous = day
            days.add(day)
        _require(
            bool(days),
            "the retained liquidation response covers a symbol with no point",
            {**context, "native_symbol": symbol},
        )
        providers.append(provider)
        symbols.append(symbol)
        pairs.append({"provider_symbol": provider, "native_symbol": symbol})
        per_symbol[symbol] = len(days)
        unique_points += len(days)
    _require(
        bool(symbols), "the retained liquidation response covers no supported symbol", context
    )
    return {
        # Both namespaces stay explicit and separately named.
        "retained_provider_symbols": sorted(providers),
        "retained_native_symbols": sorted(symbols),
        "identity_pairs": sorted(pairs, key=lambda item: item["native_symbol"]),
        "unique_in_lifecycle_points": unique_points,
        "points_per_native_symbol": dict(sorted(per_symbol.items())),
        "request_shape": "one retained request covering every listed symbol",
    }


def project_coinalyze(
    *,
    evidence: Sequence[CoinalyzeEvidence],
    supported: Sequence[str],
    unmapped: Sequence[str],
    lifecycles: Mapping[str, tuple[int, int]],
    identities: CoinalyzeIdentityMap,
    lineage: LineageManifestModel,
    staging: Path,
) -> CoinalyzeProjection:
    """Project liquidation receipts and normalized storage from real evidence only.

    Projection groups, partition keys, receipts, and lifecycle bounds are all counted in
    Binance-native identity. The retained response's Coinalyze provider identities are
    translated once, through the proved inventory binding, and both are then reported.
    """
    context = {"supported": len(supported)}
    witness = next(
        (item for item in evidence if item.role == "liquidation_charge_witness"), None
    )
    _require(witness is not None, "no accepted liquidation witness was resolved", context)
    assert witness is not None
    measured = measure_liquidation_response(witness.payload, endpoint=witness.endpoint)
    envelopes: list[dict[str, Any]] = []
    best: tuple[int, int, str] | None = None
    for reference, (provider, typed_points) in enumerate(measured["series"]):
        # The envelope is measured under the venue's own native identity.
        native = identities.native_for(provider, context=context)
        destination = staging / f"coinalyze-{native.replace('/', '_')}.parquet"
        envelope = write_liquidation_envelope(
            symbol=native,
            provider_symbol=provider,
            endpoint=witness.endpoint,
            points=typed_points,
            destination=destination,
            raw_object_ref=reference,
        )
        envelopes.append(envelope)
        # ADR-0024: typed payload per projected point, with file overhead added once per
        # projected partition. The v1 whole-file ratio is superseded here too.
        numerator = _positive_int(
            envelope["bytes_per_point"],
            field_name="typed_bytes_per_point",
            context={"native_symbol": native},
        )
        if best is None or ratio_exceeds((numerator, 1), (best[0], best[1])):
            best = (numerator, 1, native)
    _require(best is not None, "no liquidation envelope was measured", context)
    assert best is not None
    typed_footer_per_row_group = max(
        int(item["footer_per_row_group_bytes"]) for item in envelopes
    )
    typed_framing = max(int(item["framing_bytes"]) for item in envelopes)
    point_charge = int(measured["bytes_per_point"])
    framing_charge = int(measured["framing_bytes"])
    points = 0
    groups: dict[tuple[str, str], int] = {}
    for symbol in sorted(supported):
        first, last = lifecycles[symbol]
        for day in range(first, last + 1):
            month = _utc_month_of_day(day)
            # One projected observed-liquidation point per authenticated day.
            groups[(symbol, month)] = groups.get((symbol, month), 0) + 1
            points += 1
    # One symbol per request: the projected acquisition receipts are one per supported
    # mapping plus the single future-market inventory receipt.
    liquidation_receipts = len(supported)
    inventory_receipts = sum(
        1 for item in evidence if item.role == "future_market_inventory"
    )
    overlap_receipts = sum(
        1 for item in evidence if item.role == "bounded_overlap_evidence"
    )
    # Gross required raw is the exact retained inventory receipt plus the conservative
    # one-symbol-per-request liquidation projection.
    inventory = next(item for item in evidence if item.role == "future_market_inventory")
    gross_inventory = int(inventory.byte_size)
    # Raw API projection stays in raw bytes: one point charge per projected point plus
    # one response framing charge per projected request.
    gross_liquidation = points * point_charge + liquidation_receipts * framing_charge
    gross = gross_inventory + gross_liquidation
    # Retained coverage is exactly two already-retained responses: one inventory receipt
    # and one liquidation receipt whose single request carries several symbols. Their
    # credit is their own exact byte size, never a reconstruction from projected charges.
    covered = validate_retained_liquidation_coverage(
        measured,
        supported=supported,
        lifecycles=lifecycles,
        identities=identities,
        endpoint=witness.endpoint,
    )
    retained_providers = tuple(covered["retained_provider_symbols"])
    retained_natives = tuple(covered["retained_native_symbols"])
    retained_points = int(covered["unique_in_lifecycle_points"])
    retained_partitions = tuple(
        sorted(
            {
                (
                    identities.native_for(provider, context=context),
                    _utc_month_of_day(_utc_day_from_ms(int(point["event_time_ms"]))),
                )
                for provider, typed_points in measured["series"]
                for point in typed_points
            }
        )
    )
    retained_liquidation_bytes = int(witness.byte_size)
    retained_raw = gross_inventory + retained_liquidation_bytes
    _require(
        retained_raw <= gross,
        "retained Coinalyze coverage exceeds the gross requirement",
        {"gross": gross, "retained": retained_raw},
    )
    projected_new = gross - retained_raw
    numerator, denominator, envelope_witness = best
    normalized = 0
    largest = 0
    typed_payload_total = 0
    typed_overhead_total = 0
    manifest_total = 0
    manifest_mappings = 0
    for group_points in groups.values():
        payload = ceil_div(int(group_points) * numerator, denominator)
        row_groups = max(1, ceil_div(int(group_points), SIZING_ROW_BATCH))
        overhead = row_groups * typed_footer_per_row_group + typed_framing
        # ADR-0025 section 5: each Coinalyze partition carries its own lineage manifest
        # mapping its local raw reference to the retained response receipt and to the
        # proved provider/native identity pair.
        local = lineage.partition_bytes(1, kind="coinalyze")
        single_file = payload + overhead + int(local["bytes"])
        typed_payload_total += payload
        typed_overhead_total += overhead
        manifest_total += int(local["bytes"])
        manifest_mappings += int(local["mappings"])
        normalized += single_file * COINALYZE_LIQUIDATION_MULTIPLICITY
        largest = max(largest, single_file)
    return CoinalyzeProjection(
        supported_mappings=len(supported),
        typed_gaps=len(unmapped),
        point_charge_bytes=point_charge,
        framing_charge_bytes=framing_charge,
        projected_points=points,
        gross_required_raw_bytes=gross,
        gross_inventory_bytes=gross_inventory,
        gross_liquidation_bytes=gross_liquidation,
        # One retained inventory receipt and one retained liquidation receipt, whatever
        # number of symbols that single request covered.
        retained_receipts=2,
        retained_raw_bytes=retained_raw,
        retained_inventory_receipts=1,
        retained_inventory_bytes=gross_inventory,
        retained_liquidation_receipts=1,
        retained_liquidation_bytes=retained_liquidation_bytes,
        retained_provider_symbols=retained_providers,
        retained_native_symbols=retained_natives,
        retained_points=retained_points,
        retained_partitions=retained_partitions,
        projected_new_raw_bytes=projected_new,
        inventory_receipts=inventory_receipts,
        liquidation_receipts=liquidation_receipts,
        overlap_evidence_receipts=overlap_receipts,
        envelope_numerator=numerator,
        envelope_denominator=denominator,
        envelope_witness=envelope_witness,
        projected_normalized_bytes=normalized,
        projected_typed_payload_bytes=typed_payload_total,
        projected_typed_overhead_bytes=typed_overhead_total,
        projected_manifest_bytes=manifest_total,
        manifest_mappings=manifest_mappings,
        partition_count=len(groups) * COINALYZE_LIQUIDATION_MULTIPLICITY,
        largest_partition_bytes=largest,
        evidence=tuple(
            {k: v for k, v in item.to_dict().items()} for item in evidence
        ),
        envelopes=tuple(envelopes),
    )


def _unscaled(value: Decimal) -> int:
    """The exact scaled integer behind a pinned fixed-decimal value.

    Every value this module produces sits at exactly ``-DECIMAL_SCALE``, so reading its
    digit tuple is exact and, unlike arithmetic, cannot be rounded by the ambient
    decimal context. All derived arithmetic runs on these integers.
    """
    sign, digits, exponent = value.as_tuple()
    _require(
        exponent == -DECIMAL_SCALE,
        "a fixed-decimal value is not at the pinned scale",
        {"exponent": str(exponent)},
    )
    magnitude = int("".join(str(digit) for digit in digits) or "0")
    return -magnitude if sign else magnitude


def _scaled_decimal(unscaled: int) -> Decimal:
    """Rebuild a pinned fixed-decimal value from its exact scaled integer."""
    _require(
        abs(unscaled) < 10**DECIMAL_PRECISION,
        "a derived fixed-decimal value overflows the pinned precision",
        {"digits": len(str(abs(unscaled)))},
    )
    digits = tuple(int(character) for character in str(abs(unscaled))) or (0,)
    return Decimal((1 if unscaled < 0 else 0, digits, -DECIMAL_SCALE))


def _parse_typed_rows(
    sample: CohortSample, *, payload: bytes, schema_kind: str
) -> list[dict[str, Any]]:
    """Every real row of one retained sample, keyed by its family's declared fields."""
    hint = sample.family.partition("/")[2]
    declared = list(KNOWN_ARCHIVE_SCHEMAS.get(hint, {}).get("headerless", ()))
    positions = {name: index for index, name in enumerate(declared)}
    parsed: list[dict[str, Any]] = []
    for ordinal, row in enumerate(
        _iter_source_rows(
            payload, key=sample.key, family=sample.family, schema_kind=schema_kind
        )
    ):
        record: dict[str, Any] = {
            name: str(row[index]) for name, index in positions.items()
        }
        record["_ordinal"] = ordinal
        record["_symbol"] = sample.symbol
        record["_economic_interval"] = sample.economic_interval
        record["_key"] = sample.key
        parsed.append(record)
    _require(bool(parsed), "a retained sample parsed no row", {"key": sample.key})
    return parsed


def _decimal_field(
    record: Mapping[str, Any], name: str, *, key: str, product: str, ordinal: int
) -> Decimal:
    return convert_decimal(
        str(record[name]), key=key, output=product, column=name, row=ordinal
    )


@dataclass(frozen=True, slots=True)
class DerivationCohort:
    """Real retained samples for one native symbol and one economic interval.

    Derivation is causal: rows are only combined across families when they belong to the
    same symbol and the same economic interval, and joins additionally prove identical
    open and close times.
    """

    native_symbol: str
    economic_interval: str
    families: Mapping[str, list[dict[str, Any]]]
    keys: Mapping[str, str]

    def has(self, *families: str) -> bool:
        return all(family in self.families for family in families)


def group_derivation_cohorts(
    parsed: Sequence[Sequence[Mapping[str, Any]]],
) -> tuple[DerivationCohort, ...]:
    """Group real parsed samples by native symbol and economic interval."""
    grouped: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}
    keys: dict[tuple[str, str], dict[str, str]] = {}
    for rows in parsed:
        if not rows:
            continue
        head = dict(rows[0])
        symbol = str(head.get("_symbol") or "")
        interval = str(head.get("_economic_interval") or "")
        family = _family_of(str(head.get("_key") or ""))
        _require(
            bool(symbol) and bool(interval) and bool(family),
            "a parsed sample has no symbol, interval, or family",
            {"key": str(head.get("_key") or "")},
        )
        bucket = grouped.setdefault((symbol, interval), {})
        _require(
            family not in bucket,
            "two retained samples of one family share a symbol and interval",
            {"family": family, "symbol": symbol, "interval": interval},
        )
        bucket[family] = [dict(row) for row in rows]
        keys.setdefault((symbol, interval), {})[family] = str(head.get("_key") or "")
    return tuple(
        DerivationCohort(
            native_symbol=symbol,
            economic_interval=interval,
            families=families,
            keys=keys[(symbol, interval)],
        )
        for (symbol, interval), families in sorted(grouped.items())
    )


def _causal_join(
    left: Sequence[Mapping[str, Any]], right: Sequence[Mapping[str, Any]]
) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    """Inner join two families on identical open and close time, never on ordinal."""
    index: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in right:
        index[(str(row["open_time"]), str(row["close_time"]))] = row
    joined: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    for row in left:
        match = index.get((str(row["open_time"]), str(row["close_time"])))
        if match is not None:
            joined.append((row, match))
    return joined


CANONICAL_VENUE: str = "BINANCE_USDM"
UNIT_CONVENTION: str = "base_and_quote_units_as_published_by_the_venue"
CENSORSHIP_SEMANTICS: str = "observed_and_censored_aggregate_never_complete"
LIQUIDATION_OBSERVATION_LABEL: str = "censored_observed_daily_aggregate"
LIQUIDATION_SOURCE_INTERVAL_SECONDS: int = 86_400


def native_identity(native_symbol: str) -> dict[str, Any]:
    """The identity columns every final product row carries today.

    Native venue identity is real. The REF-001 canonical instrument and version ids are
    opaque fingerprints the reference store has not created for this release, so they
    stay explicitly null with a named state; their fixed encoded widths are allocated
    separately as a future Gate-3 schema charge.
    """
    return {
        "venue": CANONICAL_VENUE,
        "native_symbol": native_symbol,
        "canonical_instrument_id": None,
        "canonical_instrument_version_id": None,
        "reference_identity_state": REF_IDENTITY_STATE,
    }


def future_reference_identity_bytes(rows: int) -> dict[str, Any]:
    """The exact encoded width the not-yet-created reference identities will occupy."""
    _require(rows >= 0, "a reference width allocation has no row count", {"rows": rows})
    field_widths = {
        name: width + DICTIONARY_INDEX_WIDTH + VARIABLE_OFFSET_WIDTH + NULL_VALIDITY_WIDTH
        for name, width in FUTURE_REFERENCE_FIELD_WIDTHS.items()
    }
    per_row = sum(field_widths.values())
    return {
        "rows": rows,
        "value_widths": dict(FUTURE_REFERENCE_FIELD_WIDTHS),
        "encoded_field_widths": field_widths,
        "bytes_per_row": per_row,
        "bytes": per_row * rows,
        "allocation": (
            "schema width charge for REF-001 identities that do not exist yet; this is "
            "not an existing canonical id and no row publishes one"
        ),
    }


def cost_identity_bytes_per_row(objects: Sequence[PhysicalObject]) -> int:
    """Present-width allocation for identity fields on retained quote/depth rows."""
    _require(bool(objects), "a cost identity allocation has no object", {})
    native = max(len(item.symbol.encode("utf-8")) for item in objects)
    dictionary_overhead = DICTIONARY_INDEX_WIDTH + VARIABLE_OFFSET_WIDTH
    return (
        len(CANONICAL_VENUE.encode("utf-8"))
        + dictionary_overhead
        + native
        + dictionary_overhead
        + len(REF_IDENTITY_STATE.encode("utf-8"))
        + dictionary_overhead
        + 2 * NULL_VALIDITY_WIDTH
    )


def future_membership_term_bytes(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Conservative widths for every unavailable term on funding-only memberships."""
    unresolved = [
        row for row in rows if row.get("contract_metadata_state") == MEMBERSHIP_FUNDING_ONLY_STATE
    ]
    string_fields = (
        "contract_status",
        "underlying_type",
        "base_asset",
        "quote_asset",
        "margin_asset",
        "pair",
    )
    lifecycle_fields = ("onboard_ms", "delivery_ms", "closed_observed_ms")
    string_bytes = 0
    maximum_string_bytes = 0
    for row in unresolved:
        native_width = len(str(row["native_symbol"]).encode("utf-8"))
        row_string_bytes = len(string_fields) * (
            native_width
            + DICTIONARY_INDEX_WIDTH
            + VARIABLE_OFFSET_WIDTH
            + NULL_VALIDITY_WIDTH
        )
        string_bytes += row_string_bytes
        maximum_string_bytes = max(maximum_string_bytes, row_string_bytes)
    lifecycle_bytes = len(unresolved) * len(lifecycle_fields) * (
        INTEGER_WIDTH + NULL_VALIDITY_WIDTH
    )
    snapshot_bytes = len(unresolved) * (
        SHA256_WIDTH + VARIABLE_OFFSET_WIDTH + NULL_VALIDITY_WIDTH
    )
    fixed_row_bytes = len(lifecycle_fields) * (
        INTEGER_WIDTH + NULL_VALIDITY_WIDTH
    ) + SHA256_WIDTH + VARIABLE_OFFSET_WIDTH + NULL_VALIDITY_WIDTH
    _exact(
        len(unresolved),
        ACCEPTED_FUNDING_ONLY_MEMBERSHIP_IDENTITIES,
        field_name="funding_only_membership_rows",
        context={},
    )
    return {
        "rows": len(unresolved),
        "string_fields": list(string_fields),
        "lifecycle_fields": list(lifecycle_fields),
        "string_term_bytes": string_bytes,
        "lifecycle_term_bytes": lifecycle_bytes,
        "future_contract_snapshot_bytes": snapshot_bytes,
        "maximum_bytes_per_row": (
            maximum_string_bytes + fixed_row_bytes if unresolved else 0
        ),
        "bytes_per_row": (
            ceil_div(string_bytes + lifecycle_bytes + snapshot_bytes, len(unresolved))
            if unresolved
            else 0
        ),
        "bytes": string_bytes + lifecycle_bytes + snapshot_bytes,
        "rule": (
            "each unavailable string uses its own native-symbol width plus dictionary "
            "index, variable-value offset, and null validity; lifecycle integers and "
            "the future contract snapshot use fixed typed widths"
        ),
    }


def future_bundle_field_bytes(rows: int) -> dict[str, Any]:
    """Fixed widths of bundle values that exist only after publication."""
    fields = {
        "partition_sha256": SHA256_WIDTH + VARIABLE_OFFSET_WIDTH + NULL_VALIDITY_WIDTH,
        "lineage_manifest_sha256": (
            SHA256_WIDTH + VARIABLE_OFFSET_WIDTH + NULL_VALIDITY_WIDTH
        ),
        "partition_bytes": INTEGER_WIDTH + NULL_VALIDITY_WIDTH,
        "row_count": INTEGER_WIDTH + NULL_VALIDITY_WIDTH,
    }
    return {
        "rows": rows,
        "encoded_field_widths": fields,
        "bytes_per_row": sum(fields.values()),
        "bytes": rows * sum(fields.values()),
    }


def future_quality_gap_bound_bytes(rows: int) -> dict[str, Any]:
    fields = {
        "missing_run_start_ms": INTEGER_WIDTH,
        "missing_run_end_ms": INTEGER_WIDTH,
    }
    return {
        "rows": rows,
        "encoded_field_widths": fields,
        "bytes_per_row": sum(fields.values()),
        "bytes": rows * sum(fields.values()),
    }


def future_lineage_field_bytes(mappings: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Future archive/response receipt fields omitted from projected lineage rows."""
    projected_count = 0
    projected_responses = 0
    for item in mappings:
        if item.get("source_state") != PROJECTED_UNACQUIRED_STATE:
            continue
        projected_count += 1
        projected_responses += int(bool(item.get("provider_symbol")))
    fields = {
        "source_sha256": SHA256_WIDTH + VARIABLE_OFFSET_WIDTH + NULL_VALIDITY_WIDTH,
        "checksum_authority": SHA256_WIDTH + VARIABLE_OFFSET_WIDTH + NULL_VALIDITY_WIDTH,
        "retrieval_time": FUTURE_TIMESTAMP_WIDTH + VARIABLE_OFFSET_WIDTH + NULL_VALIDITY_WIDTH,
        "source_available_at": INTEGER_WIDTH + NULL_VALIDITY_WIDTH,
    }
    response_counter_bytes = projected_responses * 2 * (
        INTEGER_WIDTH + NULL_VALIDITY_WIDTH
    )
    return {
        "mappings": projected_count,
        "encoded_field_widths": fields,
        "bytes_per_mapping": sum(fields.values()),
        "projected_response_mappings": projected_responses,
        "future_response_counter_bytes": response_counter_bytes,
        "bytes": projected_count * sum(fields.values()) + response_counter_bytes,
    }


def projected_source_receipt_bytes(receipts: int) -> dict[str, Any]:
    """Catalog allocation for each not-yet-created acquisition receipt."""
    fields = {
        "receipt_sha256": SHA256_WIDTH + VARIABLE_OFFSET_WIDTH,
        "retrieval_time": FUTURE_TIMESTAMP_WIDTH + VARIABLE_OFFSET_WIDTH,
        "source_bytes": INTEGER_WIDTH,
        "normalized_rows": INTEGER_WIDTH,
    }
    return {
        "receipts": receipts,
        "encoded_field_widths": fields,
        "bytes_per_receipt": sum(fields.values()),
        "bytes": receipts * sum(fields.values()),
    }


def _column_values(
    columns: Sequence[TypedColumn], rows: Sequence[Mapping[str, Any]]
) -> dict[str, list[Any]]:
    """Project real row mappings onto a declared column set, blocking on a gap."""
    values: dict[str, list[Any]] = {}
    for column in columns:
        present = [row for row in rows if column.name in row]
        _require(
            len(present) == len(rows),
            "a final product row is missing a declared column",
            {"column": column.name},
        )
        values[column.name] = [row[column.name] for row in rows]
    return values


def derive_target_only_rows(
    product: str, *, cohort: DerivationCohort
) -> list[dict[str, Any]]:
    """Compute one product's target-only columns from one causal sample cohort.

    Every derived value comes from real retained rows of the same native symbol and
    economic interval. Nothing is a constant, a null placeholder, or a fabricated rate,
    and no value is combined across unrelated symbols or intervals.
    """
    columns = target_only_columns(product)
    if not columns:
        return []
    identity = native_identity(cohort.native_symbol)
    rows: list[dict[str, Any]] = []
    if product == PRODUCT_TRADE_FLOW_1H:
        family = "daily/klines"
        if not cohort.has(family):
            return []
        key = cohort.keys[family]
        for record in cohort.families[family]:
            ordinal = int(record["_ordinal"])
            volume = _decimal_field(
                record, "volume", key=key, product=product, ordinal=ordinal
            )
            quote = _decimal_field(
                record, "quote_volume", key=key, product=product, ordinal=ordinal
            )
            buy = _decimal_field(
                record, "taker_buy_volume", key=key, product=product, ordinal=ordinal
            )
            buy_quote = _decimal_field(
                record,
                "taker_buy_quote_volume",
                key=key,
                product=product,
                ordinal=ordinal,
            )
            sell = _unscaled(volume) - _unscaled(buy)
            sell_quote = _unscaled(quote) - _unscaled(buy_quote)
            rows.append(
                {
                    **identity,
                    "taker_sell_volume": _scaled_decimal(sell),
                    "taker_sell_quote_volume": _scaled_decimal(sell_quote),
                    "volume_imbalance": _scaled_decimal(_unscaled(buy) - sell),
                    "quote_volume_imbalance": _scaled_decimal(
                        _unscaled(buy_quote) - sell_quote
                    ),
                }
            )
        return rows
    if product == PRODUCT_OPEN_INTEREST_5M:
        family = "daily/metrics"
        if not cohort.has(family):
            return []
        key = cohort.keys[family]
        expected = FAMILY_CADENCE_SECONDS[family]
        previous: Decimal | None = None
        previous_value: Decimal | None = None
        previous_time: int | None = None
        for record in cohort.families[family]:
            ordinal = int(record["_ordinal"])
            level = _decimal_field(
                record, "sum_open_interest", key=key, product=product, ordinal=ordinal
            )
            value = _decimal_field(
                record,
                "sum_open_interest_value",
                key=key,
                product=product,
                ordinal=ordinal,
            )
            moment = convert_timestamp_text(
                str(record["create_time"]),
                key=key,
                output=product,
                column="create_time",
                row=ordinal,
            )
            interval = (
                None if previous_time is None else (moment - previous_time) // 1000
            )
            contiguous = interval == expected
            status = (
                "first_observation"
                if previous_time is None
                else ("contiguous" if contiguous else "gap_break")
            )
            # A discontinuity publishes no comparable and no change across the gap.
            rows.append(
                {
                    **identity,
                    "previous_sum_open_interest": previous if contiguous else None,
                    "open_interest_change": (
                        _scaled_decimal(_unscaled(level) - _unscaled(previous))
                        if contiguous and previous is not None
                        else None
                    ),
                    "open_interest_value_change": (
                        _scaled_decimal(_unscaled(value) - _unscaled(previous_value))
                        if contiguous and previous_value is not None
                        else None
                    ),
                    "change_interval_seconds": interval,
                    "gap_break_status": status,
                }
            )
            previous, previous_value, previous_time = level, value, moment
        return rows
    if product == PRODUCT_FUNDING_REALIZED:
        family = "monthly/fundingRate"
        if not cohort.has(family):
            return []
        key = cohort.keys[family]
        for record in cohort.families[family]:
            ordinal = int(record["_ordinal"])
            rate = _decimal_field(
                record, "last_funding_rate", key=key, product=product, ordinal=ordinal
            )
            rows.append(
                {
                    **identity,
                    # A positive rate is paid by longs to shorts.
                    "long_cashflow_rate": _scaled_decimal(-_unscaled(rate)),
                    "short_cashflow_rate": rate,
                    "cashflow_sign_convention": "long_pays_short_when_rate_positive",
                }
            )
        return rows
    if product == PRODUCT_FUNDING_INDICATIVE_1H:
        family = "daily/premiumIndexKlines"
        if not cohort.has(family):
            return []
        for _record in cohort.families[family]:
            rows.append(
                {
                    **identity,
                    # No retained source publishes a direct indicative rate.
                    "indicative_funding_rate": None,
                    "indicative_rate_status": "direct_indicative_rate_unavailable",
                }
            )
        return rows
    if product == PRODUCT_MARK_INDEX_BASIS_1H:
        mark_family = "daily/markPriceKlines"
        index_family = "daily/indexPriceKlines"
        premium_family = "daily/premiumIndexKlines"
        if not cohort.has(mark_family, index_family, premium_family):
            return []
        mark_key = cohort.keys[mark_family]
        index_key = cohort.keys[index_family]
        # Inner join on identical open and close time, then require the premium input
        # for the same instant. A row without all three is not causally joinable.
        joined = _causal_join(
            cohort.families[mark_family], cohort.families[index_family]
        )
        premium_index = {
            (str(row["open_time"]), str(row["close_time"])): row
            for row in cohort.families[premium_family]
        }
        for ordinal, (mark_row, index_row) in enumerate(joined):
            stamp = (str(mark_row["open_time"]), str(mark_row["close_time"]))
            if stamp not in premium_index:
                continue
            mark = _decimal_field(
                mark_row, "close", key=mark_key, product=product, ordinal=ordinal
            )
            index = _decimal_field(
                index_row, "close", key=index_key, product=product, ordinal=ordinal
            )
            index_unscaled = _unscaled(index)
            _require(
                index_unscaled != 0,
                "a relative basis has a zero index denominator",
                {"required_product": product, "row": ordinal},
            )
            basis_unscaled = _unscaled(mark) - index_unscaled
            # Deterministic fixed-decimal relative basis: exact integer arithmetic with
            # one truncating division, never a context-sensitive Decimal operation.
            relative_unscaled = (
                basis_unscaled * 10**DECIMAL_SCALE
            ) // index_unscaled
            rows.append(
                {
                    **identity,
                    "absolute_basis": _scaled_decimal(basis_unscaled),
                    "relative_basis": _scaled_decimal(relative_unscaled),
                    "basis_join_status": "causal_open_time_join",
                }
            )
        return rows
    # Identity-only products carry one row per real row of their own first family.
    families = sorted(
        item.family
        for item in contributions_for_product(product)
        if item.family in cohort.families
    )
    if not families:
        return []
    for _record in cohort.families[families[0]]:
        rows.append(dict(identity))
    return rows


def measure_target_only_columns(
    product: str, *, cohorts: Sequence[DerivationCohort], destination: Path
) -> dict[str, Any]:
    """Measure one product's target-only fields from real derived cohort values."""
    columns = target_only_columns(product)
    _require(
        bool(columns),
        "a required product declares no target-only field",
        {"required_product": product},
    )
    rows: list[dict[str, Any]] = []
    witnesses: list[str] = []
    for cohort in cohorts:
        derived = derive_target_only_rows(product, cohort=cohort)
        if not derived:
            continue
        rows.extend(derived)
        witnesses.append(f"{cohort.native_symbol}:{cohort.economic_interval}")
        break
    if not rows:
        # No real cohort supports this product's derivation. The witness is honestly
        # unavailable; nothing is invented to obtain a coefficient.
        return {
            "required_product": product,
            "target_only_columns": [column.to_dict() for column in columns],
            "witness_available": False,
            "measured_rows": 0,
            "bytes_per_row": 0,
            "payload_bytes": 0,
            "footer_bytes": 0,
            "framing_bytes": PARQUET_MAGIC_BYTES + PARQUET_TRAILER_BYTES,
            "residual_bytes": 0,
            "file_bytes": 0,
            "row_groups": 0,
            "rows": 0,
            "schema": _schema_dict(_schema_of(columns)),
            "witnesses": [],
        }
    measured = measure_fixed_schema_product(
        product=product,
        schema=_schema_of(columns),
        columns=_column_values(columns, rows),
        destination=destination,
    )
    return {
        **measured,
        "target_only_columns": [column.to_dict() for column in columns],
        "witness_available": True,
        "witnesses": witnesses,
    }


def _measure_fixed_schema_products(
    authority: SizingAuthority,
    *,
    coverage: Mapping[str, Any],
    supported: Sequence[str],
    lifecycles: Mapping[str, tuple[int, int]],
    quality_partitions: Sequence[Mapping[str, Any]],
    staging: Path,
) -> dict[str, dict[str, Any]]:
    """Measure every required product no physical archive family feeds.

    Membership comes from the accepted classifications' own evidence. Coverage is the
    accepted source-gap records preserved losslessly, with the typed-gap memberships and
    the fee-authority gaps as separate typed components. Cost calibration is five
    heterogeneous components. The bundle descriptor carries no fabricated witness value.
    """
    membership = coverage["membership"]
    snapshot = dict(authority.contract_metadata.get("symbol_snapshot") or {})
    accepted_rows = list(membership["accepted"])
    membership_rows = []
    for row in accepted_rows:
        facts = contract_evidence(row)
        symbol = facts["native_symbol"]
        digest = snapshot.get(symbol)
        membership_rows.append(
            {
                **native_identity(symbol),
                "membership_class": facts["membership_class"],
                "contract_type": facts["contract_type"],
                "contract_metadata_state": facts["contract_metadata_state"],
                "contract_evidence_class": facts["contract_evidence_class"],
                "contract_evidence_source": facts["contract_evidence_source"],
                "contract_status": facts["contract_status"],
                "underlying_type": facts["underlying_type"],
                "base_asset": facts["base_asset"],
                "quote_asset": facts["quote_asset"],
                "margin_asset": facts["margin_asset"],
                "pair": facts["pair"],
                "in_archive": facts["in_archive"],
                "in_current_exchange": facts["in_current_exchange"],
                "onboard_ms": facts["onboard_ms"],
                "delivery_ms": facts["delivery_ms"],
                "closed_observed_ms": facts["closed_observed_ms"],
                "semantics_state": facts["semantics_state"],
                # The pinned contract file maps a symbol to a snapshot digest.
                "contract_snapshot_sha256": str(digest) if digest else None,
                "evidence_records": facts["evidence_records"],
            }
        )
    _exact(
        sum(
            1
            for row in membership_rows
            if row["contract_metadata_state"] == MEMBERSHIP_DETAILED_STATE
        ),
        ACCEPTED_DETAILED_MEMBERSHIP_IDENTITIES,
        field_name="detailed_membership_identities",
        context={},
    )
    _exact(
        sum(
            1
            for row in membership_rows
            if row["contract_metadata_state"] == MEMBERSHIP_FUNDING_ONLY_STATE
        ),
        ACCEPTED_FUNDING_ONLY_MEMBERSHIP_IDENTITIES,
        field_name="funding_only_membership_identities",
        context={},
    )
    measured_membership = measure_fixed_schema_product(
        product=PRODUCT_MEMBERSHIP,
        schema=final_product_schema(PRODUCT_MEMBERSHIP),
        columns=_column_values(
            final_product_columns(PRODUCT_MEMBERSHIP), membership_rows
        ),
        destination=staging / "product-membership.parquet",
    )
    gap_rows = [
        {**native_identity(str(item["native_symbol"])), **dict(item)}
        for item in coverage["source_gaps"]
    ]
    _require(bool(gap_rows), "the accepted coverage authority has no gap row", {})
    measured_gaps = measure_fixed_schema_product(
        product=PRODUCT_COVERAGE_GAP,
        schema=final_product_schema(PRODUCT_COVERAGE_GAP),
        columns=_column_values(final_product_columns(PRODUCT_COVERAGE_GAP), gap_rows),
        destination=staging / "product-coverage-gap.parquet",
    )
    typed_rows = [
        {**native_identity(str(item["native_symbol"])), **dict(item)}
        for item in coverage["typed_gap_memberships"]
    ]
    _require(bool(typed_rows), "the accepted authority has no typed-gap membership", {})
    measured_typed = measure_fixed_schema_product(
        product="typed_gap_membership",
        schema=_schema_of(TYPED_GAP_MEMBERSHIP_COLUMNS),
        columns=_column_values(TYPED_GAP_MEMBERSHIP_COLUMNS, typed_rows),
        destination=staging / "product-typed-gap-membership.parquet",
    )
    fee_gap_rows = [
        {**native_identity(str(item["native_symbol"])), **dict(item)}
        for item in coverage["fee_gaps"]
    ]
    # ADR-0026 component four of the cost product, not a required product of its own.
    measured_fee_gaps = measure_fixed_schema_product(
        product=PRODUCT_COST_CALIBRATION,
        component="fee_authority_gap",
        schema=_schema_of(FEE_AUTHORITY_GAP_COLUMNS),
        columns=_column_values(FEE_AUTHORITY_GAP_COLUMNS, fee_gap_rows),
        destination=staging / "product-fee-authority-gap.parquet",
    )
    scenario_rows = [dict(row) for row in fee_scenario_rows()]
    # ADR-0026 component five of the cost product, not a required product of its own.
    measured_scenarios = measure_fixed_schema_product(
        product=PRODUCT_COST_CALIBRATION,
        component="scenario_policy",
        schema=_schema_of(FEE_SCENARIO_COLUMNS),
        columns=_column_values(FEE_SCENARIO_COLUMNS, scenario_rows),
        destination=staging / "product-fee-scenarios.parquet",
    )
    quality_rows = [
        {
            **native_identity(str(item["native_symbol"])),
            "required_product": str(item["required_product"]),
            "utc_month": str(item["utc_month"]),
            "missing_run_start_ms": None,
            "missing_run_end_ms": None,
            "expected_grid_count": int(item["expected_rows"]),
            "gap_kind": "projected_quality_missing_run",
            "reason": "reserved_disjoint_missing_run_on_causal_target_grid",
        }
        for item in quality_partitions
    ]
    _require(bool(quality_rows), "the projection has no fixed-cadence quality partition", {})
    measured_quality = measure_maximum_width_product(
        product="quality_gap",
        columns=QUALITY_GAP_COLUMNS,
        rows=quality_rows,
        destination=staging / "product-quality-gap.parquet",
    )
    # The official fee-schedule component has zero rows for this release, and its schema
    # is still pinned. A schema with no rows is measured as a width charge, not written.
    official_schema = _schema_of(OFFICIAL_FEE_SCHEDULE_COLUMNS)
    measured_official = measure_zero_row_schema_descriptor(
        product=PRODUCT_COST_CALIBRATION,
        component="official_fee_schedule",
        schema=official_schema,
        destination=staging / "product-official-fee-schema.parquet",
    )
    measured_official["rule"] = (
        "no free reproducible historical fee authority exists for this interval; the "
        "component schema is pinned with exactly zero rows and absence never becomes zero cost"
    )
    return {
        PRODUCT_MEMBERSHIP: measured_membership,
        PRODUCT_COVERAGE_GAP: measured_gaps,
        "typed_gap_membership": measured_typed,
        "quality_gap": measured_quality,
        "fee_authority_gap": measured_fee_gaps,
        "scenario_policy": measured_scenarios,
        "official_fee_schedule": measured_official,
        "membership_future_terms": future_membership_term_bytes(membership_rows),
    }


def measure_bundle_descriptor(
    *,
    partitions: Sequence[Mapping[str, Any]],
    coverage: Mapping[str, Any],
    schema_identities: Mapping[str, str],
    sizing_source_sha256: str,
    sizing_cli_sha256: str,
    intersections: Sequence[tuple[str, str]],
    staging: Path,
) -> dict[str, Any]:
    """Measure the final bundle descriptor from real values only.

    Nothing here invents a completed release. A partition hash, byte count, row count,
    or lineage hash that does not exist yet stays null and its fixed encoded width is
    allocated separately; every identity that already exists is pinned exactly.
    """
    _require(bool(partitions), "the bundle descriptor has no projected partition", {})
    scenario_digest = _sha256_bytes(
        canonical_json(
            {
                "scenarios": [
                    {
                        key: (
                            format(value, "f") if isinstance(value, Decimal) else value
                        )
                        for key, value in dict(row).items()
                    }
                    for row in fee_scenario_rows()
                ],
                "policy_known_at": FEE_POLICY_KNOWN_AT,
                "authority_class": FEE_AUTHORITY_CLASS,
            }
        )
    )
    configuration_digest = _sha256_bytes(
        canonical_json(
            {
                "writer_identity": writer_identity(),
                "row_group_cap": SIZING_ROW_BATCH,
                "compression": PARQUET_COMPRESSION,
                "compression_level": PARQUET_COMPRESSION_LEVEL,
                "parquet_version": PARQUET_VERSION,
                "decimal_precision": DECIMAL_PRECISION,
                "decimal_scale": DECIMAL_SCALE,
                "cadence_seconds": dict(FAMILY_CADENCE_SECONDS),
                "required_products": list(REQUIRED_PRODUCTS),
                "product_schemas": {
                    product: product_schema_contract(product)
                    for product in REQUIRED_PRODUCTS
                },
                "component_schemas": {
                    "typed_gap_membership": _schema_dict(
                        _schema_of(TYPED_GAP_MEMBERSHIP_COLUMNS)
                    ),
                    "quality_gap": _schema_dict(_schema_of(QUALITY_GAP_COLUMNS)),
                    "archive_partition_manifest": _schema_dict(
                        ARCHIVE_PARTITION_MANIFEST_SCHEMA
                    ),
                    "coinalyze_partition_manifest": _schema_dict(
                        COINALYZE_PARTITION_MANIFEST_SCHEMA
                    ),
                },
                "cost_components": list(COST_COMPONENTS),
                "fee_scenarios": [
                    {
                        key: (format(value, "f") if isinstance(value, Decimal) else value)
                        for key, value in item.items()
                    }
                    for item in fee_scenario_rows()
                ],
            }
        )
    )
    intersection_rows = [
        {"native_symbol": symbol, "utc_month": month}
        for symbol, month in intersections
    ]
    intersection_digest = _sha256_bytes(
        canonical_json({"cross_product_partition_intersection": intersection_rows})
    )
    counts = dict(coverage["counts"])
    rows = [
        {
            "required_product": str(item["required_product"]),
            "component": str(item["component"]),
            "dataset_id": (
                f"{item['required_product']}:{item['component']}:"
                f"{item['native_symbol']}:{item['utc_month']}"
            ),
            "native_symbol": str(item["native_symbol"]),
            "canonical_instrument_id": None,
            "canonical_instrument_version_id": None,
            "reference_identity_state": REF_IDENTITY_STATE,
            "utc_month": str(item["utc_month"]),
            # These exist only after Gate-3 publication; they are not invented here.
            "partition_sha256": None,
            "partition_bytes": None,
            "row_count": None,
            "schema_sha256": schema_identities[
                f"{item['required_product']}:{item['component']}"
            ],
            "lineage_manifest_sha256": None,
            "lineage_mapping_count": int(item["mappings"]),
            "source_report_sha256": ACCEPTED_REPORT_SHA256,
            "source_manifest_detail_sha256": ACCEPTED_MANIFEST_DETAIL_SHA256,
            "qualification_code_sha256": ACCEPTED_QUALIFICATION_SOURCE_SHA256,
            "qualification_cli_sha256": ACCEPTED_QUALIFICATION_CLI_SHA256,
            "sizing_code_sha256": sizing_source_sha256,
            "sizing_cli_sha256": sizing_cli_sha256,
            "configuration_sha256": configuration_digest,
            "scenario_policy_sha256": scenario_digest,
            "unit_convention": UNIT_CONVENTION,
            "censorship_semantics": CENSORSHIP_SEMANTICS,
            "coverage_gap_rows": int(counts["accepted_source_coverage_gaps"]),
            "typed_gap_membership_rows": int(counts["accepted_typed_gap_memberships"]),
            "fee_authority_gap_rows": int(counts["fee_authority_gaps"]),
            "cross_product_intersection_count": len(intersections),
            "cross_product_intersection_sha256": intersection_digest,
        }
        for item in partitions
    ]
    measured = measure_maximum_width_product(
        product=PRODUCT_BUNDLE,
        columns=final_product_columns(PRODUCT_BUNDLE),
        rows=rows,
        destination=staging / "product-bundle.parquet",
    )
    return {
        **measured,
        "scenario_policy_sha256": scenario_digest,
        "configuration_sha256": configuration_digest,
        "future_reference_identity_allocation": future_reference_identity_bytes(
            len(partitions)
        ),
        "future_partition_field_allocation": future_bundle_field_bytes(len(partitions)),
        "cross_product_partition_intersection": intersection_rows,
        "cross_product_intersection_sha256": intersection_digest,
        "unresolved_future_fields": [
            "partition_sha256",
            "partition_bytes",
            "row_count",
            "lineage_manifest_sha256",
            "canonical_instrument_id",
            "canonical_instrument_version_id",
        ],
    }


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


# --- capacity and publication ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CapacityMeasurement:
    """Real filesystem capacity, measured before and after everything durable lands."""

    destination: str
    device: str
    pre_write_available_bytes: int
    post_publication_available_bytes: int
    retained_evidence_bytes: int
    receipt_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "destination": self.destination,
            "device": self.device,
            "pre_write_available_bytes": self.pre_write_available_bytes,
            "post_publication_available_bytes": self.post_publication_available_bytes,
            "retained_sizing_evidence_bytes": self.retained_evidence_bytes,
            "durable_receipt_bytes": self.receipt_bytes,
            "accounting": (
                "retained evidence and the durable receipt are already charged against "
                "post-publication availability and are never added again"
            ),
        }


def measure_available_bytes(path: Path) -> int:
    """Available bytes on the filesystem that will actually hold the release."""
    stat = os.statvfs(str(path))
    return int(stat.f_bavail) * int(stat.f_frsize)


def device_identity(path: Path) -> str:
    return f"dev:{os.stat(str(path)).st_dev}"


def operating_reserve_bytes(pre_write_available_bytes: int) -> int:
    """The frozen reserve, derived only from measured pre-write availability."""
    return max(
        MINIMUM_OPERATING_RESERVE_BYTES,
        ceil_div(
            _positive_int(
                pre_write_available_bytes,
                field_name="pre_write_available_bytes",
                context={},
            ),
            RESERVE_DIVISOR,
        ),
    )


def _read_no_follow(path: Path) -> bytes | None:
    """Read a file only if it is a real file: a symlink at the path is never followed."""
    try:
        handle = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    except OSError as exc:
        # ELOOP means the path is a symlink; that is a refusal, not an absence.
        raise SizingError(
            "the sizing receipt target is not a regular file",
            context={"path": str(path), "errno": exc.errno},
        ) from exc
    try:
        with open(handle, "rb", closefd=True) as reader:
            return reader.read()
    except OSError as exc:
        raise SizingError(
            "the sizing receipt target is unreadable", context={"path": str(path)}
        ) from exc


# Fields whose value is a sizing-time observation rather than a stable measurement.
# `blockers`, `storage_preflight_state`, and `authorization` are frozen derivatives of
# those observations and are re-proved against the prior's own recorded values by
# `_prior_receipt_is_whole` instead of being compared with this invocation's.
VOLATILE_RECEIPT_FIELDS: tuple[str, ...] = (
    "generated_at",
    "filesystem",
    "blockers",
    "storage_preflight_state",
    "authorization",
)
VOLATILE_CAPACITY_FIELDS: tuple[str, ...] = (
    # Derived from the free space observed at this moment. Nothing else in the capacity
    # block is an observation, so nothing else belongs here.
    "operating_reserve_bytes",
    "total_future_storage_bytes",
)
STABLE_RECEIPT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "ticket",
    "policy_identity",
    "code_identity",
    "authority",
    "physical_inputs",
    "cohort",
    "typed_schema_contract",
    "lineage",
    "future_width_allocations",
    "coverage_authority",
    "cost_calibration_components",
    "fee_authority",
    "measurements",
    "projections",
    "coinalyze",
    "counts",
    "partitioning",
)
STABLE_CAPACITY_FIELDS: tuple[str, ...] = (
    "new_binance_raw_bytes",
    "new_coinalyze_raw_bytes",
    "typed_normalized_partition_bytes",
    "catalog_manifest_bundle_bytes",
    "bounded_temporary_work_bytes",
    "reserve_rule",
    # Fixed receipt policy prose. It is not an observation or a derivative of one, so it
    # is compared exactly: a prior that rewrites it is not the same receipt.
    "equation",
)


def stable_receipt_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """The one observation-independent projection of a sizing receipt.

    This is the single comparison boundary between what an invocation just measured and
    what a prior receipt recorded. It names every stable fact - schema, ticket, policy,
    code identity, accepted authority, physical inputs, cohort, typed schema, lineage,
    future widths, coverage, cost, fee, measurements, projections, Coinalyze evidence,
    semantic counts, partitioning, and the observation-independent capacity components
    plus the reserve rule - and nothing else.

    Both sides are normalized through `canonical_json`, so a structure just measured in
    memory and the same receipt decoded from its published JSON project to exactly the
    same value. Without that, an equally valid tuple, mapping, or numeric container would
    read as a difference that is a serialization artifact rather than a measurement.
    """
    capacity = dict(receipt.get("capacity") or {})
    projection: dict[str, Any] = {
        name: receipt.get(name) for name in STABLE_RECEIPT_FIELDS
    }
    projection["capacity"] = {
        name: capacity.get(name) for name in STABLE_CAPACITY_FIELDS
    }
    return json.loads(canonical_json(projection).decode("utf-8"))


def stable_receipt_identity(receipt: Mapping[str, Any]) -> str:
    """The deterministic identity of one receipt's stable projection."""
    return _sha256_bytes(canonical_json(stable_receipt_projection(receipt)))


def stable_receipt_mismatch(
    prior: Mapping[str, Any], expected: Mapping[str, Any]
) -> str | None:
    """The first stable field the two receipts disagree about, or `None`.

    Naming the field is the point: a rejected reuse must be explainable as a named
    measurement change rather than as an unexplained refusal.
    """
    left = stable_receipt_projection(prior)
    right = stable_receipt_projection(expected)
    for name in STABLE_RECEIPT_FIELDS:
        if left.get(name) != right.get(name):
            return name
    left_capacity = dict(left.get("capacity") or {})
    right_capacity = dict(right.get("capacity") or {})
    for name in STABLE_CAPACITY_FIELDS:
        if left_capacity.get(name) != right_capacity.get(name):
            return f"capacity.{name}"
    return None


def revalidate_prior_receipt(
    receipt_path: Path, *, expected: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    """The complete prior receipt, or nothing at all.

    Two separate proofs must both pass. First, every stable identity this invocation just
    measured - authority, code, cohort, measurements, projections, counts, partitioning,
    and the capacity components that do not depend on sizing-time observation - must equal
    what the prior recorded. Second, the prior must be internally whole: its own canonical
    length, filesystem block, frozen reserve, capacity sum, blockers, state, and
    authorization must all agree with each other.

    A newly observed free-space value and the reserve derived from it are deliberately not
    compared: they are observations of this moment, not properties of the frozen receipt.
    """
    body = _read_no_follow(receipt_path)
    if body is None:
        return None
    try:
        prior = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(prior, dict):
        return None
    # Canonical reserialization alone is not identity; the stored bytes must be exactly
    # the canonical form of what they decode to.
    if canonical_json(prior) != body:
        return None
    # One boundary, both directions: any named stable difference rejects reuse.
    if stable_receipt_mismatch(prior, expected) is not None:
        return None
    if not _prior_receipt_is_whole(prior, body=body):
        return None
    return prior


def _prior_receipt_is_whole(prior: Mapping[str, Any], *, body: bytes) -> bool:
    """Every stored field agrees with every other stored field, and with its own bytes."""
    capacity = dict(prior.get("capacity") or {})
    filesystem = dict(prior.get("filesystem") or {})
    reserve = capacity.get("operating_reserve_bytes")
    total = capacity.get("total_future_storage_bytes")
    components = [
        capacity.get(name)
        for name in (
            "new_binance_raw_bytes",
            "new_coinalyze_raw_bytes",
            "typed_normalized_partition_bytes",
            "catalog_manifest_bundle_bytes",
            "bounded_temporary_work_bytes",
            "operating_reserve_bytes",
        )
    ]
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in components
    ):
        return False
    if isinstance(reserve, bool) or not isinstance(reserve, int) or reserve <= 0:
        return False
    if reserve < MINIMUM_OPERATING_RESERVE_BYTES:
        return False
    if not isinstance(total, int) or isinstance(total, bool) or total != sum(components):
        return False
    for name in (
        "destination",
        "device",
        "pre_write_available_bytes",
        "post_publication_available_bytes",
        "retained_sizing_evidence_bytes",
        "durable_receipt_bytes",
    ):
        if name not in filesystem:
            return False
    declared_length = filesystem.get("durable_receipt_bytes")
    if (
        isinstance(declared_length, bool)
        or not isinstance(declared_length, int)
        or declared_length != len(body)
    ):
        return False
    pre_write = filesystem.get("pre_write_available_bytes")
    post = filesystem.get("post_publication_available_bytes")
    for value in (pre_write, post, filesystem.get("retained_sizing_evidence_bytes")):
        if isinstance(value, bool) or not isinstance(value, int):
            return False
    # The frozen reserve must still be the reserve its own recorded availability implies.
    if reserve != operating_reserve_bytes(int(pre_write)):
        return False
    blockers = prior.get("blockers")
    state = prior.get("storage_preflight_state")
    if not isinstance(blockers, list) or state not in {STATE_SUFFICIENT, STATE_BLOCKED}:
        return False
    if sorted(set(str(item) for item in blockers)) != list(blockers):
        return False
    expected_blocked = int(total) > int(post)
    if expected_blocked and BLOCKER_CAPACITY not in blockers:
        return False
    if not expected_blocked and BLOCKER_CAPACITY in blockers:
        return False
    if (state == STATE_BLOCKED) != bool(blockers):
        return False
    if "authorizes no acquisition" not in str(prior.get("authorization") or ""):
        return False
    return True


def _open_directory_no_follow(path: Path, *, label: str) -> int:
    """A descriptor for a directory that was not reached through any symbolic link.

    Every later operation - staging, linking, comparing, fsyncing, cleaning up - uses
    this descriptor rather than the pathname, so a component swapped after the check
    cannot redirect the write.
    """
    try:
        handle = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise SizingError(
            f"the {label} directory is not a real directory",
            context={"path": str(path), "errno": exc.errno},
        ) from exc
    return handle


def _require_no_symlink(path: Path, *, label: str) -> None:
    """No component of a publication target may be a symbolic link."""
    current = path
    seen: set[str] = set()
    while True:
        text = str(current)
        if text in seen:
            break
        seen.add(text)
        if current.is_symlink():
            raise SizingError(
                f"the {label} target path contains a symbolic link",
                context={"path": str(path), "component": text},
            )
        parent = current.parent
        if parent == current:
            break
        current = parent


def _stream_copy(source: Path, handle: Any) -> tuple[str, int]:
    """Copy one file through bounded reads, hashing as it goes. Never whole-file."""
    digest = hashlib.sha256()
    written = 0
    with source.open("rb") as reader:
        while True:
            chunk = reader.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
            written += len(chunk)
    return digest.hexdigest(), written


def _hash_at_no_follow(directory: int, name: str) -> str | None:
    """Hash an existing target through its directory descriptor, following no link."""
    try:
        handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SizingError(
            "an existing publication target is not a regular file",
            context={"name": name, "errno": exc.errno},
        ) from exc
    digest = hashlib.sha256()
    with open(handle, "rb", closefd=True) as reader:
        while True:
            chunk = reader.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _read_at_no_follow(directory: int, name: str) -> bytes | None:
    try:
        handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SizingError(
            "an existing publication target is not a regular file",
            context={"name": name, "errno": exc.errno},
        ) from exc
    with open(handle, "rb", closefd=True) as reader:
        return reader.read()


def _publish_at(
    *, directory: int, name: str, label: str, write: Any, expected: bytes | None = None
) -> None:
    """Stage, link, fsync, and clean up entirely through one validated directory fd."""
    # ``mkstemp`` takes no directory descriptor, so the temporary is created explicitly
    # and exclusively relative to the validated one.
    tmp_name = f".partial-{name}.{os.urandom(8).hex()}.tmp"
    handle_fd = os.open(
        tmp_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory,
    )
    try:
        with open(handle_fd, "wb", closefd=True) as handle:
            write(handle)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # A link cannot replace a racing destination, so a concurrent nonidentical
            # publication is never overwritten, and a racing symlink is refused.
            os.link(tmp_name, name, src_dir_fd=directory, dst_dir_fd=directory)
        except FileExistsError:
            existing = _read_at_no_follow(directory, name)
            if expected is None or existing != expected:
                raise SizingError(
                    f"a different {label} already occupies its target",
                    context={"name": name},
                ) from None
            return
        os.fsync(directory)
    finally:
        try:
            os.unlink(tmp_name, dir_fd=directory)
        except FileNotFoundError:
            pass


def publish_sizing_envelope(source: Path, *, evidence_root: Path) -> tuple[Path, bool]:
    """Publish one envelope content-addressably, streamed, no-follow, and only once."""
    root = Path(evidence_root)
    root.mkdir(parents=True, exist_ok=True)
    _require_no_symlink(root, label="sizing evidence root")
    digest = compute_sha256(source)
    name = f"{digest}.parquet"
    dest = root / name
    _require(
        (root / name).resolve().parent == root.resolve(),
        "a sizing envelope escapes its evidence root",
        {"path": str(dest)},
    )
    directory = _open_directory_no_follow(root, label="sizing evidence root")
    try:
        existing = _hash_at_no_follow(directory, name)
        if existing is not None:
            _require(
                existing == digest,
                "an existing sizing envelope does not match its content address",
                {"path": str(dest), "expected": digest, "actual": existing},
            )
            return dest, True

        def _write(handle: Any) -> None:
            streamed, _size = _stream_copy(source, handle)
            if streamed != digest:
                raise SizingError(
                    "the staged sizing envelope does not match its content address",
                    context={"expected": digest, "actual": streamed},
                )

        _publish_at(
            directory=directory, name=name, label="sizing envelope", write=_write
        )
        published = _hash_at_no_follow(directory, name)
        _require(
            published == digest,
            "the published sizing envelope failed its post-write rehash",
            {"path": str(dest)},
        )
    finally:
        os.close(directory)
    return dest, False


def publish_sizing_receipt(receipt: Mapping[str, Any], *, path: Path) -> tuple[str, int]:
    """Publish the canonical receipt at its fixed target, byte-identical or not at all."""
    body = canonical_json(receipt)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    _require_no_symlink(path, label="sizing receipt")
    directory = _open_directory_no_follow(parent, label="sizing receipt")
    try:
        _publish_at(
            directory=directory,
            name=path.name,
            label="sizing receipt",
            write=lambda handle: handle.write(body),
            expected=body,
        )
    finally:
        os.close(directory)
    return _sha256_bytes(body), len(body)


# --- receipt and orchestration ---------------------------------------------------------


def sizing_code_identity(*, module_path: Path, cli_path: Path) -> dict[str, str]:
    """The executing sizing bytes, named rather than asserted."""
    return {
        "policy_identity": SIZING_POLICY_IDENTITY,
        "sizing_source_sha256": file_sha256(module_path),
        "sizing_cli_sha256": file_sha256(cli_path) if cli_path.is_file() else "",
        "pyarrow_version": str(pa.__version__),
        "writer_identity": writer_identity(),
    }


def run_storage_sizing(
    paths: AuthorityPaths,
    *,
    receipt_path: Path,
    sizing_source_path: Path,
    sizing_cli_path: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Measure, project, publish, and report. No network, no acquisition, no gate.

    Everything that can fail closed runs before anything durable is written: authority,
    cohort accounting, exact physical inputs, the accepted acquisition credit, and the
    full reconciliation. Only then are envelopes and the fixed receipt published.
    """
    generated_at = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
    store = paths.store_root
    authority = load_sizing_authority(paths)
    cohort = derive_sample_cohort(authority)
    selected, detail_counts = resolve_selected_objects(paths.manifest_detail_path)
    cost, cost_counts = resolve_cost_objects(
        authority, listing_cache_dir=paths.listing_cache_dir
    )
    checkpoint = dict(authority.progress_checkpoint.get("objects") or {})
    # The Gate-2 retained credit is re-proved over the complete selected-plus-cost
    # requirement, path-bound and proved object by object. It is deliberately not the
    # sizing cohort and not the manifest's separate consumable count, and its keys,
    # objects, and bytes stay three separate facts.
    credit = prove_retained_acquisition_credit(
        selected,
        cost,
        report=authority.report,
        checkpoint=checkpoint,
        sample_dir=paths.sample_dir,
        sidecar_dir=paths.sidecar_dir,
    )
    reconciliation = reconcile_physical_inputs(
        selected=selected,
        cost=cost,
        retained_credit_objects=int(credit["objects"]),
        retained_credit_bytes=int(credit["bytes"]),
    )
    coinalyze_evidence = resolve_coinalyze_evidence(
        authority, cache_dir=paths.coinalyze_cache_dir
    )
    inventory = next(
        item for item in coinalyze_evidence if item.role == "future_market_inventory"
    )
    # The two Coinalyze namespaces are bound once, from the pinned inventory, and every
    # later comparison uses that proved binding rather than a reshaped string.
    identities = prove_coinalyze_identity_map(authority, inventory=inventory)
    supported, unmapped = coinalyze_symbol_sets(
        authority, inventory=inventory, identities=identities
    )
    lifecycles, cutoff = coinalyze_lifecycles(authority, supported=supported)

    schema_contract = prove_product_contract()
    lineage = bind_sample_lineage(
        authority.report, checkpoint=checkpoint, cohort=cohort
    )
    lineage_bindings = dict(lineage["bindings"])
    lineage_decomposition = prove_accepted_lineage_decomposition(
        lineage["decomposition"]
    )
    coverage = prove_coverage_authority(authority.report)
    objects = tuple(selected) + tuple(cost)
    retained_archive_bindings = build_retained_archive_bindings(
        credit=credit,
        checkpoint=checkpoint,
        objects=objects,
        sample_bindings=lineage_bindings,
    )

    evidence_root = store / SIZING_EVIDENCE_ROOT
    _require(
        V1_SIZING_EVIDENCE_ROOT not in str(evidence_root),
        "version-2 sizing may never write into the immutable version-1 evidence root",
        {"evidence_root": str(evidence_root)},
    )
    _require(
        not str(receipt_path).endswith(V1_SIZING_RECEIPT_RELATIVE_PATH.rsplit("/", 1)[-1]),
        "version-2 sizing may never rewrite the accepted version-1 receipt",
        {"receipt_path": str(receipt_path)},
    )
    pre_write = measure_available_bytes(store)
    measurements: list[TypedEnvelopeMeasurement] = []
    parsed_samples: list[list[dict[str, Any]]] = []
    published = 0
    reused = 0
    # The evidence set is identified by content address, so it is the same set whether
    # this invocation wrote the objects or found them already published. Publication
    # outcomes are operational facts and never reach the durable receipt.
    envelope_digests: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="cex002-sizing-") as staging:
        stage = Path(staging)
        for sample in cohort:
            payload, schema_kind = verify_retained_sample(
                sample,
                sample_dir=paths.sample_dir,
                sidecar_dir=paths.sidecar_dir,
                checkpoint=checkpoint,
            )
            parsed_samples.append(
                _parse_typed_rows(sample, payload=payload, schema_kind=schema_kind)
            )
            stem = _sha256_bytes(sample.key.encode("utf-8"))
            for output in contributions_for_family(sample.family):
                envelope = stage / f"{stem}-{output.name.replace(':', '-')}.parquet"
                measurements.append(
                    measure_typed_envelope(
                        sample,
                        payload=payload,
                        output=output,
                        destination=envelope,
                        schema_kind=schema_kind,
                    )
                )
                _dest, was_reused = publish_sizing_envelope(
                    envelope, evidence_root=evidence_root
                )
                envelope_digests.add(_dest.stem)
                reused += int(was_reused)
                published += int(not was_reused)
        # ADR-0025 section 5 and review 236 finding 6: build the projected partition
        # set first, then measure a real lineage manifest for two actual partitions so
        # payload per mapping and fixed per-partition overhead are separated by
        # measurement rather than by dividing a cohort-global file.
        partition_mappings = build_partition_lineage(
            retained_archive_bindings,
            objects=objects,
            retained_credit_keys=credit["keys"],
        )
        archive_lineage = reconcile_archive_lineage(
            partition_mappings,
            requirement_keys=[item.key for item in objects],
            retained_credit_keys=credit["keys"],
            coefficient_keys=[item.key for item in cohort],
        )
        _exact(
            archive_lineage["retained_archive_requirement_keys"],
            credit["valid_requirement_keys"],
            field_name="retained_archive_requirement_keys",
            context={},
        )
        _exact(
            archive_lineage["retained_archive_key_set_sha256"],
            credit["key_set_sha256"],
            field_name="retained_archive_key_set_sha256",
            context={},
        )
        projected_coinalyze_partitions = [
            (symbol, month)
            for symbol in sorted(supported)
            for month in {
                _utc_month_of_day(day)
                for day in range(lifecycles[symbol][0], lifecycles[symbol][1] + 1)
            }
        ]
        witness = next(
            item
            for item in coinalyze_evidence
            if item.role == "liquidation_charge_witness"
        )
        retained_coinalyze_partitions = retained_coinalyze_partition_keys(
            coinalyze_evidence, identities=identities
        )
        coinalyze_mappings = coinalyze_partition_lineage(
            partitions=projected_coinalyze_partitions,
            receipt_sha256=witness.sha256,
            receipt_endpoint=witness.endpoint,
            identities=identities,
            availability="retained_coinalyze_response_receipt",
            retrieval_time=None,
            retained_partitions=retained_coinalyze_partitions,
        )
        lineage_model = model_partition_lineage(
            partition_mappings,
            coinalyze_partitions=coinalyze_mappings,
            staging=stage,
        )
        for envelope in sorted(stage.glob("lineage-*-partition-*.parquet")):
            _dest, was_reused = publish_sizing_envelope(
                envelope, evidence_root=evidence_root
            )
            envelope_digests.add(_dest.stem)
            reused += int(was_reused)
            published += int(not was_reused)
        # ADR-0025 section 2: target-only fields are measured from real derived values
        # grouped causally by native symbol and economic interval.
        cohorts = group_derivation_cohorts(parsed_samples)
        target_only: dict[str, dict[str, Any]] = {}
        for product in REQUIRED_PRODUCTS:
            if not contributions_for_product(product) or not target_only_columns(product):
                continue
            target_only[product] = measure_target_only_columns(
                product,
                cohorts=cohorts,
                destination=stage / f"target-{product}.parquet",
            )
        for envelope in sorted(stage.glob("target-*.parquet")):
            _dest, was_reused = publish_sizing_envelope(
                envelope, evidence_root=evidence_root
            )
            envelope_digests.add(_dest.stem)
            reused += int(was_reused)
            published += int(not was_reused)
        cost_identity_rate = cost_identity_bytes_per_row(cost)
        projections = project_typed_partitions(
            measurements=measurements,
            objects=objects,
            lineage=lineage_model,
            target_only_bytes_per_row={
                **{
                    product: int(value["bytes_per_row"])
                    for product, value in target_only.items()
                },
                f"{PRODUCT_COST_CALIBRATION}:retained_book_ticker": cost_identity_rate,
                f"{PRODUCT_COST_CALIBRATION}:retained_book_depth": cost_identity_rate,
            },
        )
        coinalyze = project_coinalyze(
            evidence=coinalyze_evidence,
            supported=supported,
            unmapped=unmapped,
            lifecycles=lifecycles,
            identities=identities,
            lineage=lineage_model,
            staging=stage,
        )
        anchors = prove_coinalyze_anchor_identity(
            authority,
            identities=identities,
            retained_provider_symbols=coinalyze.retained_provider_symbols,
        )
        for envelope in sorted(stage.glob("coinalyze-*.parquet")):
            _dest, was_reused = publish_sizing_envelope(envelope, evidence_root=evidence_root)
            envelope_digests.add(_dest.stem)
            reused += int(was_reused)
            published += int(not was_reused)
        fixed_products = _measure_fixed_schema_products(
            authority,
            coverage=coverage,
            supported=supported,
            lifecycles=lifecycles,
            quality_partitions=[
                partition
                for projection in projections
                if projection.component == "target_product"
                and all(
                    family_cadence_seconds(component["physical_family"]) > 0
                    for component in projection.components
                )
                for partition in projection.partitions
            ],
            staging=stage,
        )
        all_partitions = {**partition_mappings, **coinalyze_mappings}
        intersections = cross_product_partition_intersection(all_partitions)
        bundle_descriptor = measure_bundle_descriptor(
            partitions=[
                {
                    "required_product": product,
                    "component": component,
                    "native_symbol": symbol,
                    "utc_month": month,
                    "mappings": len(mappings),
                }
                for (product, component, symbol, month), mappings in sorted(
                    all_partitions.items()
                )
            ],
            coverage=coverage,
            schema_identities={
                f"{product}:{component}": partition_schema_identity(product, component)
                for product, component, _symbol, _month in all_partitions
            },
            sizing_source_sha256=file_sha256(sizing_source_path),
            sizing_cli_sha256=file_sha256(sizing_cli_path),
            intersections=intersections,
            staging=stage,
        )
        for envelope in sorted(stage.glob("product-*.parquet")):
            _dest, was_reused = publish_sizing_envelope(envelope, evidence_root=evidence_root)
            envelope_digests.add(_dest.stem)
            reused += int(was_reused)
            published += int(not was_reused)

    membership_rows = int(coverage["counts"]["accepted_membership_identities"])
    # The non-archive products are projected from their own measured typed rows.
    membership_projection = project_fixed_schema_product(
        fixed_products[PRODUCT_MEMBERSHIP],
        rows=membership_rows,
        partitions=membership_rows,
        partition_rows=[1] * membership_rows,
    )
    typed_gap_partition_rows = partition_row_counts(
        coverage["typed_gap_memberships"],
        fields=("required_product", "native_symbol"),
    )
    typed_gap_projection = project_fixed_schema_product(
        fixed_products["typed_gap_membership"],
        rows=int(coverage["counts"]["accepted_typed_gap_memberships"]),
        partitions=len(typed_gap_partition_rows),
        partition_rows=typed_gap_partition_rows,
    )
    fee_gap_projection = project_fixed_schema_product(
        fixed_products["fee_authority_gap"],
        rows=int(coverage["counts"]["fee_authority_gaps"]),
        partitions=membership_rows,
        partition_rows=[1] * membership_rows,
    )
    # ADR-0025 section 6: known source gaps, fee-authority gaps, and the row-level
    # quality reservation are separate counts and none replaces another.
    known_gap_rows = int(coverage["counts"]["known_coverage_rows"])
    # ADR-0025 section 6: sum ceil(expected_rows / 2) independently for every projected
    # fixed-cadence partition. Event-driven products reserve no inferred absence.
    quality_gap_partitions = [
        partition
        for item in projections
        if item.component == "target_product"
        and all(
            family_cadence_seconds(component["physical_family"]) > 0
            for component in item.components
        )
        for partition in item.partitions
    ]
    quality_gap_rows = sum(
        quality_gap_reservation(rows)
        for item in projections
        if item.component == "target_product"
        and all(
            family_cadence_seconds(component["physical_family"]) > 0
            for component in item.components
        )
        for rows in item.partition_rows
    )
    source_gap_partition_rows = partition_row_counts(
        coverage["source_gaps"], fields=("required_product", "native_symbol")
    )
    gap_projection = project_fixed_schema_product(
        fixed_products[PRODUCT_COVERAGE_GAP],
        rows=int(coverage["counts"]["accepted_source_coverage_gaps"]),
        partitions=len(source_gap_partition_rows),
        partition_rows=source_gap_partition_rows,
    )
    quality_gap_projection = project_fixed_schema_product(
        fixed_products["quality_gap"],
        rows=quality_gap_rows,
        partitions=len(quality_gap_partitions),
        partition_rows=[
            quality_gap_reservation(int(item["expected_rows"]))
            for item in quality_gap_partitions
        ],
    )
    scenario_projection = project_fixed_schema_product(
        fixed_products["scenario_policy"],
        rows=len(FEE_SCENARIOS),
        partitions=1,
        partition_rows=[len(FEE_SCENARIOS)],
    )
    # ADR-0026 component three: pinned schema, exactly zero rows, never zero cost.
    official_fee_projection = project_fixed_schema_product(
        fixed_products["official_fee_schedule"], rows=0, partitions=1, partition_rows=[0]
    )
    retained_cost = {
        item.component: item
        for item in projections
        if item.product == PRODUCT_COST_CALIBRATION
    }
    cost_components = {
        "retained_book_ticker": {
            **retained_cost["retained_book_ticker"].to_dict(),
            "contribution": f"{PRODUCT_COST_CALIBRATION}:daily_book_ticker",
            "catalog_pages": retained_cost["retained_book_ticker"].partition_count,
        },
        "retained_book_depth": {
            **retained_cost["retained_book_depth"].to_dict(),
            "contribution": f"{PRODUCT_COST_CALIBRATION}:daily_book_depth",
            "catalog_pages": retained_cost["retained_book_depth"].partition_count,
        },
        "official_fee_schedule": {
            **dict(official_fee_projection),
            "catalog_pages": 1,
        },
        "fee_authority_gap": {
            **dict(fee_gap_projection),
            "catalog_pages": int(fee_gap_projection["partition_count"]),
        },
        "scenario_policy": {
            **dict(scenario_projection),
            "catalog_pages": int(scenario_projection["partition_count"]),
        },
    }
    cost_calibration_bytes = sum(
        int(item["projected_bytes"]) for item in cost_components.values()
    )
    archive_partitions = sum(item.partition_count for item in projections)
    partition_count = (
        archive_partitions
        + coinalyze.partition_count
        + membership_projection["partition_count"]
        + gap_projection["partition_count"]
        + typed_gap_projection["partition_count"]
        + fee_gap_projection["partition_count"]
        + scenario_projection["partition_count"]
        + quality_gap_projection["partition_count"]
        + official_fee_projection["partition_count"]
        + 1  # the bundle descriptor table
    )
    bundle_projection = project_fixed_schema_product(
        bundle_descriptor,
        rows=int(bundle_descriptor["measured_rows"]),
        partitions=1,
        partition_rows=[int(bundle_descriptor["measured_rows"])],
    )
    typed_normalized_bytes = (
        sum(item.projected_bytes for item in projections)
        + int(membership_projection["projected_bytes"])
        + int(gap_projection["projected_bytes"])
        + int(bundle_projection["projected_bytes"])
        + int(scenario_projection["projected_bytes"])
        + int(typed_gap_projection["projected_bytes"])
        + int(fee_gap_projection["projected_bytes"])
        + int(quality_gap_projection["projected_bytes"])
        + int(official_fee_projection["projected_bytes"])
    )
    # The catalog charges the projected acquisition receipt set, not the five bounded
    # qualification provenance records.
    projected_receipts = (
        len(objects) + coinalyze.inventory_receipts + coinalyze.liquidation_receipts
    )
    bundle_rows = int(bundle_descriptor["measured_rows"])
    local_manifests = archive_partitions + coinalyze.partition_count
    archive_target_partitions = sum(
        item.partition_count
        for item in projections
        if item.product != PRODUCT_COST_CALIBRATION
    )
    catalog_page_components = {
        "archive_target_data_partitions": archive_target_partitions,
        "cost_book_ticker_data_partitions": retained_cost[
            "retained_book_ticker"
        ].partition_count,
        "cost_book_depth_data_partitions": retained_cost[
            "retained_book_depth"
        ].partition_count,
        "coinalyze_data_partitions": coinalyze.partition_count,
        "membership_partitions": int(membership_projection["partition_count"]),
        "source_gap_partitions": int(gap_projection["partition_count"]),
        "typed_gap_partitions": int(typed_gap_projection["partition_count"]),
        "quality_gap_partitions": int(quality_gap_projection["partition_count"]),
        "fee_gap_partitions": int(fee_gap_projection["partition_count"]),
        "scenario_partitions": int(scenario_projection["partition_count"]),
        "official_zero_row_schema_descriptors": 1,
        "local_partition_manifests": local_manifests,
        "bundle_descriptor_rows": bundle_rows,
        "projected_acquisition_receipts": projected_receipts,
    }
    catalog_pages = sum(catalog_page_components.values())
    # Lineage mappings are already charged inside each product partition. What remains
    # here is the catalog transaction itself plus the two pinned authority artifacts.
    partition_manifest_bytes = (
        sum(item.projected_manifest_bytes for item in projections)
        + coinalyze.projected_manifest_bytes
    )
    identity_rows = (
        sum(item.projected_rows for item in projections)
        + coinalyze.projected_points
        + membership_rows
        + int(gap_projection["projected_rows"])
        + int(typed_gap_projection["projected_rows"])
        + int(fee_gap_projection["projected_rows"])
        + int(quality_gap_projection["projected_rows"])
        + bundle_rows
    )
    future_width_allocations = {
        "reference_identity": future_reference_identity_bytes(identity_rows),
        "membership_terms": dict(fixed_products["membership_future_terms"]),
        "bundle_partition_fields": future_bundle_field_bytes(bundle_rows),
        "quality_gap_bounds": future_quality_gap_bound_bytes(quality_gap_rows),
        "lineage_receipt_fields": future_lineage_field_bytes(
            row
            for mappings in (*partition_mappings.values(), *coinalyze_mappings.values())
            for row in mappings
        ),
        "projected_source_receipts": projected_source_receipt_bytes(projected_receipts),
    }
    future_normalized_bytes = sum(
        int(future_width_allocations[name]["bytes"])
        for name in (
            "reference_identity",
            "membership_terms",
            "bundle_partition_fields",
            "quality_gap_bounds",
            "lineage_receipt_fields",
        )
    )
    projected_receipt_allocation = int(
        future_width_allocations["projected_source_receipts"]["bytes"]
    )
    catalog_bytes = (
        catalog_pages * CATALOG_PAGE_BYTES
        + ACCEPTED_REPORT_BYTES
        + ACCEPTED_MANIFEST_DETAIL_BYTES
        + projected_receipt_allocation
    )
    normalized_bytes = (
        typed_normalized_bytes
        + coinalyze.projected_normalized_bytes
        + future_normalized_bytes
    )
    largest_current_partition = max(
        max((item.largest_partition_bytes for item in projections), default=0),
        coinalyze.largest_partition_bytes,
        int(membership_projection["largest_partition_bytes"]),
        int(gap_projection["largest_partition_bytes"]),
        int(bundle_projection["largest_partition_bytes"]),
        int(scenario_projection["largest_partition_bytes"]),
        int(typed_gap_projection["largest_partition_bytes"]),
        int(fee_gap_projection["largest_partition_bytes"]),
        int(quality_gap_projection["largest_partition_bytes"]),
        int(official_fee_projection["largest_partition_bytes"]),
    )
    maximum_identity_rows = max(
        bundle_rows,
        31,  # one projected daily Coinalyze point per day in a UTC month
        max(
            (rows for item in projections for rows in item.partition_rows),
            default=0,
        ),
        max(source_gap_partition_rows, default=0),
        max(typed_gap_partition_rows, default=0),
        max(
            (
                quality_gap_reservation(int(item["expected_rows"]))
                for item in quality_gap_partitions
            ),
            default=0,
        ),
        1,
    )
    reference_partition_charge = (
        maximum_identity_rows
        * int(future_width_allocations["reference_identity"]["bytes_per_row"])
    )
    lineage_width = future_width_allocations["lineage_receipt_fields"]
    lineage_partition_charge = max(
        (
            sum(
                1
                for row in mappings
                if row.get("source_state") == PROJECTED_UNACQUIRED_STATE
            )
            * int(lineage_width["bytes_per_mapping"])
            + sum(
                1
                for row in mappings
                if row.get("source_state") == PROJECTED_UNACQUIRED_STATE
                and row.get("provider_symbol")
            )
            * 2
            * (INTEGER_WIDTH + NULL_VALIDITY_WIDTH)
            for mappings in (*partition_mappings.values(), *coinalyze_mappings.values())
        ),
        default=0,
    )
    reference_width = int(
        future_width_allocations["reference_identity"]["bytes_per_row"]
    )
    maximum_quality_rows = max(
        (
            quality_gap_reservation(int(item["expected_rows"]))
            for item in quality_gap_partitions
        ),
        default=0,
    )
    largest_future_partition_charge = max(
        reference_partition_charge,
        reference_width
        + int(future_width_allocations["membership_terms"]["maximum_bytes_per_row"]),
        bundle_rows * reference_width
        + int(future_width_allocations["bundle_partition_fields"]["bytes"]),
        maximum_quality_rows
        * (
            reference_width
            + int(future_width_allocations["quality_gap_bounds"]["bytes_per_row"])
        ),
        lineage_partition_charge,
    )
    # The eventual partition contains its current typed bytes and its future fields.
    # Adding the independently greatest two terms is conservative even when they occur
    # in different partitions and therefore cannot understate the atomic work unit.
    largest_partition = largest_current_partition + largest_future_partition_charge
    # ADR-0024 section 5: partition-atomic publication renames one verified temporary
    # partition into its final content-addressed path, so there is no second complete
    # normalized allocation. The bounded work unit is the greatest single explicit unit.
    bundle_transaction_bytes = catalog_bytes
    temporary_work = max(
        ACCEPTED_LARGEST_SELECTED_OBJECT_BYTES,
        largest_partition,
        bundle_transaction_bytes,
    )
    evidence_bytes = sum(
        int(path.stat().st_size)
        for path in evidence_root.glob("*.parquet")
        if path.is_file()
    )
    available_after_evidence = measure_available_bytes(store)
    reserve = operating_reserve_bytes(pre_write)
    components = {
        "new_binance_raw_bytes": reconciliation["projected_new_binance_raw_bytes"],
        "new_coinalyze_raw_bytes": coinalyze.projected_new_raw_bytes,
        "typed_normalized_partition_bytes": normalized_bytes,
        "catalog_manifest_bundle_bytes": catalog_bytes,
        "bounded_temporary_work_bytes": temporary_work,
        "operating_reserve_bytes": reserve,
    }
    fixed_projection_set = (
        membership_projection,
        gap_projection,
        typed_gap_projection,
        quality_gap_projection,
        fee_gap_projection,
        scenario_projection,
        official_fee_projection,
        bundle_projection,
    )
    normalized_payload_bytes = (
        sum(item.projected_payload_bytes for item in projections)
        + coinalyze.projected_typed_payload_bytes
        + sum(int(item["projected_payload_bytes"]) for item in fixed_projection_set)
        + future_normalized_bytes
    )
    normalized_overhead_bytes = (
        sum(item.projected_overhead_bytes for item in projections)
        + coinalyze.projected_typed_overhead_bytes
        + sum(int(item["projected_overhead_bytes"]) for item in fixed_projection_set)
    )
    _exact(
        normalized_payload_bytes + normalized_overhead_bytes + partition_manifest_bytes,
        normalized_bytes,
        field_name="typed_normalized_byte_equation",
        context={},
    )
    body: dict[str, Any] = {
        "schema_version": SIZING_SCHEMA_VERSION,
        "ticket": TICKET_ID,
        "policy_identity": SIZING_POLICY_IDENTITY,
        "code_identity": sizing_code_identity(
            module_path=sizing_source_path, cli_path=sizing_cli_path
        ),
        "authority": {
            "report_path": str(paths.report_path),
            "manifest_detail_path": str(paths.manifest_detail_path),
            "listing_checkpoint_path": str(paths.listing_checkpoint_path),
            "progress_checkpoint_path": str(paths.progress_checkpoint_path),
            "contract_metadata_path": str(paths.contract_metadata_path),
            "report_bytes": ACCEPTED_REPORT_BYTES,
            "manifest_detail_bytes": ACCEPTED_MANIFEST_DETAIL_BYTES,
            "manifest_detail_records": detail_counts["record_count"],
            "plan_version": ACCEPTED_PLAN_VERSION,
            "plan_entries": ACCEPTED_PLAN_ENTRIES,
            "plan_actions": dict(ACCEPTED_PLAN_ACTIONS),
            "bindings": dict(authority.bindings),
        },
        "physical_inputs": {
            **reconciliation,
            # ADR-0023 keeps these two authorities separately visible: the manifest's own
            # consumable publication fact, and the re-proved Gate-2 retained credit.
            "manifest_consumable_rows": detail_counts["manifest_consumable_rows"],
            "retained_credit": dict(credit),
            "listing_responses_used": cost_counts["listing_responses_used"],
            "archive_families": list(ARCHIVE_FAMILIES),
            "cost_families": list(COST_FAMILIES),
        },
        "cohort": {
            "unique_samples": len(cohort),
            "expected_unique_samples": ACCEPTED_SAMPLE_COHORT,
            "role": "coefficient measurement only; never acquisition credit",
            "alias_folded_keys": sorted(item.key for item in cohort if item.aliases),
            "samples": [
                {
                    "key": item.key,
                    "family": item.family,
                    "symbol": item.symbol,
                    "economic_interval": item.economic_interval,
                    "action": item.action,
                    "aliases": item.aliases,
                }
                for item in cohort
            ],
        },
        "typed_schema_contract": schema_contract,
        "lineage": {
            **lineage_decomposition,
            **archive_lineage,
            "bound_cohort_keys": lineage["decomposition"]["bound_cohort_keys"],
            "retrieval_time_known_bindings": sum(
                1
                for item in retained_archive_bindings.values()
                if item["retrieval_time"]
            ),
            "retrieval_time_unknown_bindings": sum(
                1
                for item in retained_archive_bindings.values()
                if not item["retrieval_time"]
            ),
        },
        "future_width_allocations": future_width_allocations,
        "coverage_authority": {
            **dict(coverage["counts"]),
            "projected_quality_gap_rows": quality_gap_rows,
            "quality_gap_rule": (
                "ceil(expected_rows / 2) disjoint missing runs, summed per projected "
                "fixed-cadence partition and never after product aggregation"
            ),
            "source_gap_component": dict(gap_projection),
            "typed_gap_membership_component": dict(typed_gap_projection),
            "quality_gap_component": dict(quality_gap_projection),
            "fee_authority_gap_component": dict(fee_gap_projection),
            "rule": str(coverage["rule"]),
        },
        "cost_calibration_components": {
            "retained_book_ticker": {
                "schema": _schema_dict(
                    _schema_of(cost_component_columns("retained_book_ticker"))
                ),
                "contribution": f"{PRODUCT_COST_CALIBRATION}:daily_book_ticker",
            },
            "retained_book_depth": {
                "schema": _schema_dict(
                    _schema_of(cost_component_columns("retained_book_depth"))
                ),
                "contribution": f"{PRODUCT_COST_CALIBRATION}:daily_book_depth",
            },
            **{
                name: {
                    **dict(value),
                    "schema": _schema_dict(_schema_of(cost_component_columns(name))),
                }
                for name, value in cost_components.items()
            },
            "projected_rows": sum(
                int(value["projected_rows"]) for value in cost_components.values()
            ),
            "partition_count": sum(
                int(value["partition_count"]) for value in cost_components.values()
            ),
            "projected_bytes": cost_calibration_bytes,
            "byte_equation": (
                "retained book ticker + retained book depth + zero-row official schema "
                "+ fee-authority gaps + scenario policy, each allocated once"
            ),
            "rule": (
                "five heterogeneous ADR-0026 components, each with its own schema, rows, "
                "and allocation, summed once into the cost product"
            ),
        },
        "fee_authority": {
            "official_historical_rows": ACCEPTED_OFFICIAL_FEE_ROWS,
            "official_component_schema": _schema_dict(
                _schema_of(OFFICIAL_FEE_SCHEDULE_COLUMNS)
            ),
            "fee_authority_gaps": int(coverage["counts"]["fee_authority_gaps"]),
            "gap_kind": FEE_GAP_KIND,
            "scenario_policy_rows": [
                {
                    key: (format(value, "f") if isinstance(value, Decimal) else value)
                    for key, value in row.items()
                }
                for row in fee_scenario_rows()
            ],
            "policy_known_at": FEE_POLICY_KNOWN_AT,
            "authority_class": FEE_AUTHORITY_CLASS,
            "rule": (
                "no free reproducible historical fee authority exists for this interval; "
                "absence is published as typed gaps and outcome-blind policy rows, never "
                "as a backdated observation, a zero cost, a rebate, or a maker credit"
            ),
        },
        "measurements": [item.to_dict() for item in measurements],
        "projections": {
            "row_batch_cap": SIZING_ROW_BATCH,
            "writer_identity": writer_identity(),
            "arithmetic": "integer cross multiplication and ceiling division only",
            "required_products": [item.to_dict() for item in projections],
            "fixed_schema_products": {
                PRODUCT_MEMBERSHIP: dict(membership_projection),
                PRODUCT_COVERAGE_GAP: dict(gap_projection),
                PRODUCT_BUNDLE: dict(bundle_projection),
                "scenario_policy": dict(scenario_projection),
                "typed_gap_membership": dict(typed_gap_projection),
                "quality_gap": dict(quality_gap_projection),
                "fee_authority_gap": dict(fee_gap_projection),
                "official_fee_schedule": dict(official_fee_projection),
            },
            "final_product_schemas": {
                product: product_schema_contract(product)
                for product in REQUIRED_PRODUCTS
            },
            "target_only_fields": {
                product: {
                    "columns": [
                        column.to_dict() for column in target_only_columns(product)
                    ],
                    "bytes_per_row": int(
                        dict(target_only.get(product) or {}).get("bytes_per_row") or 0
                    ),
                    "measured_rows": int(
                        dict(target_only.get(product) or {}).get("measured_rows") or 0
                    ),
                }
                for product in REQUIRED_PRODUCTS
            },
            "target_only_bytes": sum(
                item.projected_target_only_bytes for item in projections
            ),
            "lineage_manifest_model": lineage_model.to_dict(),
            "typed_normalized_bytes": normalized_bytes,
            "typed_payload_bytes": normalized_payload_bytes,
            "future_field_payload_bytes": future_normalized_bytes,
            "typed_overhead_bytes": normalized_overhead_bytes,
            "typed_partition_manifest_bytes": partition_manifest_bytes,
            "projected_rows": sum(item.projected_rows for item in projections),
            "projected_row_groups": sum(
                item.projected_row_groups for item in projections
            ),
            "partition_lineage": {
                "model": lineage_model.to_dict(),
                "partitions": len(partition_mappings),
                "mappings": sum(len(value) for value in partition_mappings.values()),
                "coinalyze_partitions": coinalyze.partition_count,
                "coinalyze_mappings": coinalyze.manifest_mappings,
            },
            "superseded_rule": (
                "the version-1 greatest whole-file ratio is superseded: payload and "
                "file overhead are projected separately, per partition"
            ),
        },
        "coinalyze": {
            **coinalyze.to_dict(),
            "cutoff": cutoff,
            # Native identity, and named as such: these are Binance symbols.
            "supported_native_symbols": list(supported),
            "unmapped_native_symbols": list(unmapped),
            "identity_map": identities.to_dict(),
            "anchor_identity": dict(anchors),
        },
        "counts": {
            "physical_raw_objects": len(objects),
            "projected_normalized_files": partition_count,
            "typed_gap_rows": len(unmapped),
            "membership_rows": membership_rows,
            "projected_coinalyze_receipts": (
                coinalyze.inventory_receipts + coinalyze.liquidation_receipts
            ),
            "projected_acquisition_receipts": projected_receipts,
            "retained_coinalyze_evidence_records": len(coinalyze_evidence),
            # Semantic: the number of distinct content-addressed sizing envelopes this
            # release measures, never a count of write-versus-reuse attempts.
            "sizing_envelopes": len(envelope_digests),
            "required_products": len(REQUIRED_PRODUCTS),
            "product_contributions": len(PRODUCT_CONTRIBUTIONS),
            **{
                f"coverage_{name}": value
                for name, value in dict(coverage["counts"]).items()
            },
            # The membership boundary is exposed by its own names as well: total
            # classifications, accepted identities, and proved exclusions.
            "membership_classifications": int(
                coverage["counts"]["membership_classifications"]
            ),
            "accepted_membership_identities": int(
                coverage["counts"]["accepted_membership_identities"]
            ),
            "rejected_membership_rows": int(
                coverage["counts"]["rejected_membership_rows"]
            ),
            "projected_quality_gap_rows": quality_gap_rows,
            "coverage_rows_total": known_gap_rows + quality_gap_rows,
            "logical_sample_records": lineage_decomposition["logical_records"],
            "physical_sample_bindings": lineage_decomposition["physical_bindings"],
            "folded_sample_aliases": lineage_decomposition["folded_aliases"],
            "partition_manifest_mappings": sum(
                len(value) for value in partition_mappings.values()
            ),
            "partition_manifest_projected_mappings": sum(
                item.manifest_mappings for item in projections
            ) + coinalyze.manifest_mappings,
            "catalog_pages": catalog_pages,
            "catalog_page_components": catalog_page_components,
            "count_sources": {
                "physical_raw_objects": "manifest detail rows plus accepted cost keys",
                "projected_normalized_files": (
                    "logical product, symbol, and UTC-month partitions"
                ),
                "typed_gap_rows": "report coinalyze universe_support.unmapped_symbols",
                "membership_rows": "report membership.classifications",
                "projected_coinalyze_receipts": (
                    "one liquidation receipt per supported mapping plus one inventory"
                ),
                "retained_coinalyze_evidence_records": "report coinalyze.provenance",
            },
        },
        "partitioning": {
            "rule": (
                "one content-addressed file per logical product/component, native symbol, "
                "and UTC month"
            ),
            "publication": (
                "partition-atomic: a verified temporary partition is renamed into its "
                "content-addressed final path, so the normalized output is allocated "
                "once and no second complete release tree is staged"
            ),
            "partition_count": partition_count,
            "catalog_page_bytes": CATALOG_PAGE_BYTES,
            "catalog_overhead_bytes": catalog_bytes,
            "partition_manifest_bytes": partition_manifest_bytes,
            "partition_manifest_payload_bytes_per_mapping": (
                lineage_model.payload_bytes_per_mapping
            ),
            "partition_manifest_model": lineage_model.to_dict(),
            "archive_product_partitions": archive_partitions,
            "coinalyze_product_partitions": coinalyze.partition_count,
            "cross_product_partition_intersection": [
                {"native_symbol": symbol, "utc_month": month}
                for symbol, month in intersections
            ],
            "cross_product_intersection_sha256": bundle_descriptor[
                "cross_product_intersection_sha256"
            ],
            "bundle_transaction_bytes": bundle_transaction_bytes,
            "largest_projected_partition_bytes": largest_partition,
            "largest_current_typed_partition_bytes": largest_current_partition,
            "largest_future_width_charge_bytes": largest_future_partition_charge,
            "largest_accepted_object_bytes": ACCEPTED_LARGEST_SELECTED_OBJECT_BYTES,
            "immutable_v1_evidence": {
                "receipt_relative_path": V1_SIZING_RECEIPT_RELATIVE_PATH,
                "receipt_sha256": V1_ACCEPTED_RECEIPT_SHA256,
                "evidence_root": V1_SIZING_EVIDENCE_ROOT,
                "rule": "never read, rewritten, reused, or deleted by version 2",
            },
        },
        "capacity": {
            **components,
            "total_future_storage_bytes": sum(components.values()),
            "reserve_rule": "max(16 GiB, ceil(pre_write_available / 5)), never lowered",
            "equation": (
                "new Binance raw + new Coinalyze raw + typed normalized partitions + "
                "catalog/manifest/bundle + bounded temporary work + operating reserve, "
                "counted once and without overlap"
            ),
        },
    }
    prior = revalidate_prior_receipt(receipt_path, expected=body)
    if prior is not None:
        # A fully re-proved prior receipt is the receipt: rerunning never rewrites it,
        # and no observation of published, reused, or free space can change it.
        stored = receipt_path.read_bytes()
        return {
            "receipt": prior,
            "receipt_file": {
                "receipt_sha256": _sha256_bytes(stored),
                "receipt_bytes": len(stored),
            },
            "publication": {
                "rerun": True,
                "envelopes_published": published,
                "envelopes_reused": reused,
                "available_bytes_after_evidence": available_after_evidence,
            },
        }

    total = sum(components.values())
    # The receipt accounts for its own exact final canonical length, so sufficiency is
    # compared with the space that remains after the evidence and this receipt.
    receipt_bytes = 0
    receipt: dict[str, Any] = {}
    for _ in range(4):
        capacity = CapacityMeasurement(
            destination=str(store),
            device=device_identity(store),
            pre_write_available_bytes=pre_write,
            post_publication_available_bytes=available_after_evidence - receipt_bytes,
            retained_evidence_bytes=evidence_bytes,
            receipt_bytes=receipt_bytes,
        )
        blockers: list[str] = []
        for _name, value in sorted(components.items()):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                blockers.append(BLOCKER_UNKNOWN)
        archive_products = {
            item.product for item in PRODUCT_CONTRIBUTIONS
        }
        if {item.product for item in projections} != archive_products:
            blockers.append(BLOCKER_TYPED)
        if total > capacity.post_publication_available_bytes:
            blockers.append(BLOCKER_CAPACITY)
        receipt = {
            **body,
            "generated_at": generated_at,
            "filesystem": capacity.to_dict(),
            "blockers": sorted(set(blockers)),
            "storage_preflight_state": STATE_BLOCKED if blockers else STATE_SUFFICIENT,
            "authorization": (
                "a sufficient storage preflight is a measurement only: it accepts no "
                "gate, authorizes no acquisition, and changes no ticket state"
            ),
        }
        measured_length = len(canonical_json(receipt))
        if measured_length == receipt_bytes:
            break
        receipt_bytes = measured_length
    # One canonical boundary. The self-sized receipt is encoded and decoded exactly once
    # here, so the document that is published, the document that is returned, and the
    # document a later rerun revalidates from the target bytes are the same document -
    # not merely three structures that happen to serialize to equal bytes.
    receipt = json.loads(canonical_json(receipt).decode("utf-8"))
    _exact(
        len(canonical_json(receipt)),
        receipt_bytes,
        field_name="durable_receipt_bytes",
        context={"path": str(receipt_path)},
    )
    digest, published_bytes = publish_sizing_receipt(receipt, path=receipt_path)
    _exact(
        published_bytes,
        receipt_bytes,
        field_name="published_receipt_bytes",
        context={"path": str(receipt_path)},
    )
    return {
        "receipt": receipt,
        "receipt_file": {"receipt_sha256": digest, "receipt_bytes": published_bytes},
        "publication": {
            "rerun": False,
            "envelopes_published": published,
            "envelopes_reused": reused,
            "available_bytes_after_evidence": available_after_evidence,
        },
    }
