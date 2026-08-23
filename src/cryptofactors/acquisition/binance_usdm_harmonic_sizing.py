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
import struct
import tempfile
import zipfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
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
SIZING_SCHEMA_VERSION: str = "cex002_gate2_storage_sizing_v1"
SIZING_POLICY_IDENTITY: str = "adr0021_review181_bounded_real_sample_storage_sizing_v1"

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

SIZING_EVIDENCE_ROOT: str = "evidence/sizing/v1/envelopes/sha256"
SIZING_RECEIPT_RELATIVE_PATH: str = (
    "research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json"
)
STATE_SUFFICIENT: str = "sufficient"
STATE_BLOCKED: str = "blocked"

BLOCKER_AUTHORITY: str = "accepted_authority_mismatch"
BLOCKER_INPUTS: str = "physical_input_reconciliation_failed"
BLOCKER_COHORT: str = "sample_cohort_incomplete"
BLOCKER_COINALYZE: str = "coinalyze_projection_incomplete"
BLOCKER_CAPACITY: str = "available_capacity_insufficient"
BLOCKER_UNKNOWN: str = "component_unknown_or_non_integer"


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


@dataclass(frozen=True, slots=True)
class EnvelopeMeasurement:
    """What one real object costs in a lossless deterministic normalized envelope."""

    key: str
    family: str
    symbol: str
    economic_interval: str
    schema_kind: str
    compressed_archive_bytes: int
    extracted_member_bytes: int
    source_rows: int
    arrow_ipc_bytes: int
    parquet_bytes: int
    parquet_footer_bytes: int
    parquet_file_overhead_bytes: int
    parquet_sha256: str
    writer_identity: str
    pyarrow_version: str
    batches: int

    def ratio(self) -> tuple[int, int]:
        return (self.parquet_bytes, self.compressed_archive_bytes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "family": self.family,
            "symbol": self.symbol,
            "economic_interval": self.economic_interval,
            "schema_kind": self.schema_kind,
            "compressed_archive_bytes": self.compressed_archive_bytes,
            "extracted_member_bytes": self.extracted_member_bytes,
            "source_rows": self.source_rows,
            "arrow_ipc_bytes": self.arrow_ipc_bytes,
            "parquet_bytes": self.parquet_bytes,
            "parquet_footer_bytes": self.parquet_footer_bytes,
            "parquet_file_overhead_bytes": self.parquet_file_overhead_bytes,
            "parquet_sha256": self.parquet_sha256,
            "writer_identity": self.writer_identity,
            "pyarrow_version": self.pyarrow_version,
            "batches": self.batches,
            "row_batch_cap": SIZING_ROW_BATCH,
        }


def writer_identity() -> str:
    """The deterministic writer settings, named exactly as they are applied."""
    return (
        f"pyarrow{pa.__version__}_parquet{PARQUET_VERSION}_{PARQUET_COMPRESSION}"
        f"l{PARQUET_COMPRESSION_LEVEL}_rowgroup{SIZING_ROW_BATCH}_nostats_v1"
    )


def envelope_schema(family: str) -> pa.Schema:
    """Identity columns plus every declared source token, all preserved as written."""
    hint = family.partition("/")[2]
    fields = KNOWN_ARCHIVE_SCHEMAS.get(hint, {}).get("headerless", ())
    if not fields:
        raise SizingError("no declared schema for physical family", context={"family": family})
    columns = [
        pa.field("physical_family", pa.string(), nullable=False),
        pa.field("venue_symbol", pa.string(), nullable=False),
        pa.field("economic_interval", pa.string(), nullable=False),
        pa.field("source_key", pa.string(), nullable=False),
        pa.field("source_row_ordinal", pa.int64(), nullable=False),
    ]
    columns.extend(pa.field(str(name), pa.string(), nullable=False) for name in fields)
    return pa.schema(columns)


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


def measure_sample_envelope(
    sample: CohortSample,
    *,
    payload: bytes,
    destination: Path,
    schema_kind: str,
) -> EnvelopeMeasurement:
    """Write the lossless envelope for one object and measure exactly what it cost."""
    schema = envelope_schema(sample.family)
    token_names = [field.name for field in schema][5:]
    member = safe_zip_member(payload, key=sample.key)
    rows = 0
    batches = 0
    arrow_bytes = 0
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
                arrow_bytes += _write_batch(
                    writer, schema, batch, sample=sample, ordinal=rows, tokens=token_names
                )
                rows += len(batch)
                batches += 1
                batch = []
        if batch:
            arrow_bytes += _write_batch(
                writer, schema, batch, sample=sample, ordinal=rows, tokens=token_names
            )
            rows += len(batch)
            batches += 1
    finally:
        writer.close()
    _require(rows > 0, "the retained sample parsed no rows", {"key": sample.key})
    parquet_bytes = int(destination.stat().st_size)
    footer_bytes, overhead = _parquet_footer_bytes(destination)
    return EnvelopeMeasurement(
        key=sample.key,
        family=sample.family,
        symbol=sample.symbol,
        economic_interval=sample.economic_interval,
        schema_kind=schema_kind,
        compressed_archive_bytes=len(payload),
        extracted_member_bytes=int(member.file_size),
        source_rows=rows,
        arrow_ipc_bytes=arrow_bytes,
        parquet_bytes=parquet_bytes,
        parquet_footer_bytes=footer_bytes,
        parquet_file_overhead_bytes=overhead,
        parquet_sha256=compute_sha256(destination),
        writer_identity=writer_identity(),
        pyarrow_version=str(pa.__version__),
        batches=batches,
    )


def _write_batch(
    writer: pq.ParquetWriter,
    schema: pa.Schema,
    batch: Sequence[Sequence[str]],
    *,
    sample: CohortSample,
    ordinal: int,
    tokens: Sequence[str],
) -> int:
    """One deterministic row group, measured in uncompressed Arrow IPC bytes."""
    columns: dict[str, list[Any]] = {
        "physical_family": [sample.family] * len(batch),
        "venue_symbol": [sample.symbol] * len(batch),
        "economic_interval": [sample.economic_interval] * len(batch),
        "source_key": [sample.key] * len(batch),
        "source_row_ordinal": [ordinal + index for index in range(len(batch))],
    }
    for position, name in enumerate(tokens):
        columns[name] = [row[position] for row in batch]
    table = pa.Table.from_pydict(columns, schema=schema)
    writer.write_table(table, row_group_size=SIZING_ROW_BATCH)
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, schema) as stream:
        stream.write_table(table)
    return int(len(sink.getvalue()))


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
class FamilyProjection:
    """One family's worst observed real expansion, applied by exact integer arithmetic."""

    family: str
    numerator: int
    denominator: int
    witness_key: str
    sample_count: int
    input_compressed_bytes: int
    input_objects: int
    multiplicity: int
    partition_count: int
    projected_bytes: int
    largest_partition_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "ratio_numerator_parquet_bytes": self.numerator,
            "ratio_denominator_compressed_bytes": self.denominator,
            "ratio_selection": "greatest exact rational by cross multiplication",
            "witness_key": self.witness_key,
            "sample_count": self.sample_count,
            "input_objects": self.input_objects,
            "input_compressed_bytes": self.input_compressed_bytes,
            "output_multiplicity": self.multiplicity,
            "partition_count": self.partition_count,
            "ceiling_operation": (
                "sum over symbol-month groups of "
                "ceil(group_bytes * numerator / denominator) * multiplicity"
            ),
            "projected_bytes": self.projected_bytes,
            "largest_partition_bytes": self.largest_partition_bytes,
            "largest_partition_rule": "one logical output file, before fan-out",
        }


def family_coefficients(
    measurements: Sequence[EnvelopeMeasurement],
) -> dict[str, tuple[int, int, str, int]]:
    """The greatest observed exact rational parquet/compressed ratio per family."""
    best: dict[str, tuple[int, int, str]] = {}
    counts: dict[str, int] = {}
    for item in measurements:
        counts[item.family] = counts.get(item.family, 0) + 1
        numerator = _positive_int(
            item.parquet_bytes, field_name="parquet_bytes", context={"key": item.key}
        )
        denominator = _positive_int(
            item.compressed_archive_bytes,
            field_name="compressed_archive_bytes",
            context={"key": item.key},
        )
        current = best.get(item.family)
        if current is None or ratio_exceeds((numerator, denominator), (current[0], current[1])):
            best[item.family] = (numerator, denominator, item.key)
    return {
        family: (value[0], value[1], value[2], counts[family])
        for family, value in best.items()
    }


def group_objects(
    objects: Sequence[PhysicalObject],
) -> dict[tuple[str, str, str], int]:
    """Exact symbol/UTC-month/source-family groups: one output file per group."""
    groups: dict[tuple[str, str, str], int] = {}
    for item in objects:
        key = (item.family, item.symbol, utc_month(item.economic_interval))
        groups[key] = groups.get(key, 0) + item.byte_size
    return groups


def project_families(
    *,
    measurements: Sequence[EnvelopeMeasurement],
    objects: Sequence[PhysicalObject],
) -> tuple[FamilyProjection, ...]:
    """Project every family from its own coefficient and its own grouped input bytes."""
    coefficients = family_coefficients(measurements)
    groups = group_objects(objects)
    counts: dict[str, int] = {}
    for item in objects:
        counts[item.family] = counts.get(item.family, 0) + 1
    projections: list[FamilyProjection] = []
    for family in PHYSICAL_FAMILIES:
        _require(
            family in coefficients,
            "a physical family has no measured coefficient",
            {"family": family},
        )
        numerator, denominator, witness, measured = coefficients[family]
        multiplicity = OUTPUT_MULTIPLICITY[family]
        family_groups = {
            key: value for key, value in groups.items() if key[0] == family
        }
        _require(
            bool(family_groups),
            "a physical family has no grouped input bytes",
            {"family": family},
        )
        total = 0
        largest = 0
        for group_bytes in family_groups.values():
            # One logical file per group per multiplicity: the family total carries the
            # fan-out, but the high-water partition is a single file, not the fan-out sum.
            single_file = ceil_div(int(group_bytes) * numerator, denominator)
            total += single_file * multiplicity
            largest = max(largest, single_file)
        projections.append(
            FamilyProjection(
                family=family,
                numerator=numerator,
                denominator=denominator,
                witness_key=witness,
                sample_count=measured,
                input_compressed_bytes=sum(family_groups.values()),
                input_objects=counts.get(family, 0),
                multiplicity=multiplicity,
                partition_count=len(family_groups) * multiplicity,
                projected_bytes=total,
                largest_partition_bytes=largest,
            )
        )
    return tuple(projections)


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
        record = snapshot.get(symbol) or {}
        onboard = record.get("onboard_ms") if isinstance(record, dict) else None
        close = record.get("close_ms") if isinstance(record, dict) else None
        if onboard is None:
            evidence = rows.get(symbol) or {}
            for item in (evidence.get("evidence") or ()) if isinstance(evidence, dict) else ():
                if isinstance(item, dict) and item.get("onboard_ms") is not None:
                    onboard = item.get("onboard_ms")
                    close = item.get("close_ms", close)
                    break
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
    projected_new_raw_bytes: int
    inventory_receipts: int
    liquidation_receipts: int
    overlap_evidence_receipts: int
    envelope_numerator: int
    envelope_denominator: int
    envelope_witness: str
    projected_normalized_bytes: int
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
            "partition_count": self.partition_count,
            "largest_partition_bytes": self.largest_partition_bytes,
            "evidence": [dict(item) for item in self.evidence],
            "envelopes": [dict(item) for item in self.envelopes],
        }


LIQUIDATION_ENVELOPE_SCHEMA: pa.Schema = pa.schema(
    [
        pa.field("venue_symbol", pa.string(), nullable=False),
        pa.field("endpoint", pa.string(), nullable=False),
        pa.field("point_ordinal", pa.int64(), nullable=False),
        pa.field("point_token", pa.string(), nullable=False),
    ]
)


def measure_liquidation_response(payload: bytes, *, endpoint: str) -> dict[str, Any]:
    """Exact framing and per-point charges from the real retained liquidation response."""
    context = {"endpoint": endpoint}
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SizingError(
            "the retained liquidation response is not JSON", context=context
        ) from exc
    _require(
        isinstance(document, list) and bool(document),
        "the retained liquidation response is empty",
        context,
    )
    series: list[tuple[str, list[str]]] = []
    points = 0
    point_bytes = 0
    for row in document:
        _require(isinstance(row, dict), "a liquidation series is not an object", context)
        symbol = str(row.get("symbol") or "")
        history = row.get("history")
        _require(isinstance(history, list), "a liquidation series has no history", context)
        tokens: list[str] = []
        for point in history:
            _require(isinstance(point, dict), "a liquidation point is not an object", context)
            token = json.dumps(point, sort_keys=True, separators=(",", ":"))
            tokens.append(token)
            point_bytes += len(token.encode("utf-8"))
            points += 1
        series.append((symbol, tokens))
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
    tokens: Sequence[str],
    destination: Path,
) -> dict[str, Any]:
    """One deterministic lossless liquidation envelope, measured exactly.

    ``symbol`` is the Binance-native identity written into the ``venue_symbol`` column;
    ``provider_symbol`` is the Coinalyze identity the retained response used. Both are
    reported, and neither is derived from the other.
    """
    _require(
        bool(tokens),
        "a liquidation series has no point to normalize",
        {"native_symbol": symbol, "provider_symbol": provider_symbol},
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw_bytes = sum(len(token.encode("utf-8")) for token in tokens)
    writer = pq.ParquetWriter(
        str(destination),
        LIQUIDATION_ENVELOPE_SCHEMA,
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
        version=PARQUET_VERSION,
        write_statistics=False,
        store_schema=True,
    )
    try:
        for start in range(0, len(tokens), SIZING_ROW_BATCH):
            chunk = list(tokens[start : start + SIZING_ROW_BATCH])
            table = pa.Table.from_pydict(
                {
                    "venue_symbol": [symbol] * len(chunk),
                    "endpoint": [endpoint] * len(chunk),
                    "point_ordinal": [start + index for index in range(len(chunk))],
                    "point_token": chunk,
                },
                schema=LIQUIDATION_ENVELOPE_SCHEMA,
            )
            writer.write_table(table, row_group_size=SIZING_ROW_BATCH)
    finally:
        writer.close()
    parquet_bytes = int(destination.stat().st_size)
    footer_bytes, overhead = _parquet_footer_bytes(destination)
    return {
        "venue_symbol": symbol,
        "native_symbol": symbol,
        "provider_symbol": provider_symbol,
        "endpoint": endpoint,
        "points": len(tokens),
        "raw_point_bytes": raw_bytes,
        "parquet_bytes": parquet_bytes,
        "parquet_footer_bytes": footer_bytes,
        "parquet_file_overhead_bytes": overhead,
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
    for provider, tokens in measured["series"]:
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
        for token in tokens:
            point = json.loads(token)
            moment = point.get("t")
            _require(
                isinstance(moment, int) and not isinstance(moment, bool) and moment > 0,
                "a retained liquidation point has no positive timestamp",
                {**context, "native_symbol": symbol},
            )
            day = datetime.fromtimestamp(int(moment), UTC).date().toordinal()
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
    for provider, tokens in measured["series"]:
        # The envelope is measured under the venue's own native identity.
        native = identities.native_for(provider, context=context)
        destination = staging / f"coinalyze-{native.replace('/', '_')}.parquet"
        envelope = write_liquidation_envelope(
            symbol=native,
            provider_symbol=provider,
            endpoint=witness.endpoint,
            tokens=tokens,
            destination=destination,
        )
        envelopes.append(envelope)
        numerator = _positive_int(
            envelope["parquet_bytes"],
            field_name="parquet_bytes",
            context={"native_symbol": native},
        )
        denominator = _positive_int(
            envelope["raw_point_bytes"],
            field_name="raw_point_bytes",
            context={"native_symbol": native},
        )
        if best is None or ratio_exceeds((numerator, denominator), (best[0], best[1])):
            best = (numerator, denominator, native)
    _require(best is not None, "no liquidation envelope was measured", context)
    assert best is not None
    point_charge = int(measured["bytes_per_point"])
    framing_charge = int(measured["framing_bytes"])
    points = 0
    groups: dict[tuple[str, str], int] = {}
    for symbol in sorted(supported):
        first, last = lifecycles[symbol]
        for day in range(first, last + 1):
            month = _utc_month_of_day(day)
            groups[(symbol, month)] = groups.get((symbol, month), 0) + point_charge
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
    for group_bytes in groups.values():
        single_file = ceil_div(int(group_bytes) * numerator, denominator)
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
        projected_new_raw_bytes=projected_new,
        inventory_receipts=inventory_receipts,
        liquidation_receipts=liquidation_receipts,
        overlap_evidence_receipts=overlap_receipts,
        envelope_numerator=numerator,
        envelope_denominator=denominator,
        envelope_witness=envelope_witness,
        projected_normalized_bytes=normalized,
        partition_count=len(groups) * COINALYZE_LIQUIDATION_MULTIPLICITY,
        largest_partition_bytes=largest,
        evidence=tuple(
            {k: v for k, v in item.to_dict().items()} for item in evidence
        ),
        envelopes=tuple(envelopes),
    )


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
VOLATILE_RECEIPT_FIELDS: tuple[str, ...] = ("generated_at", "filesystem")
STABLE_RECEIPT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "ticket",
    "policy_identity",
    "code_identity",
    "authority",
    "physical_inputs",
    "cohort",
    "measurements",
    "projections",
    "coinalyze",
    "counts",
    "partitioning",
)
STABLE_CAPACITY_FIELDS: tuple[str, ...] = (
    "new_binance_raw_bytes",
    "new_coinalyze_raw_bytes",
    "normalized_catalog_bytes",
    "temporary_high_water_bytes",
    "reserve_rule",
)


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
    for field_name in STABLE_RECEIPT_FIELDS:
        if prior.get(field_name) != expected.get(field_name):
            return None
    prior_capacity = dict(prior.get("capacity") or {})
    expected_capacity = dict(expected.get("capacity") or {})
    for field_name in STABLE_CAPACITY_FIELDS:
        if prior_capacity.get(field_name) != expected_capacity.get(field_name):
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
            "normalized_catalog_bytes",
            "temporary_high_water_bytes",
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

    evidence_root = store / SIZING_EVIDENCE_ROOT
    pre_write = measure_available_bytes(store)
    measurements: list[EnvelopeMeasurement] = []
    published = 0
    reused = 0
    with tempfile.TemporaryDirectory(prefix="cex002-sizing-") as staging:
        stage = Path(staging)
        for sample in cohort:
            payload, schema_kind = verify_retained_sample(
                sample,
                sample_dir=paths.sample_dir,
                sidecar_dir=paths.sidecar_dir,
                checkpoint=checkpoint,
            )
            envelope = stage / f"{_sha256_bytes(sample.key.encode('utf-8'))}.parquet"
            measurements.append(
                measure_sample_envelope(
                    sample,
                    payload=payload,
                    destination=envelope,
                    schema_kind=schema_kind,
                )
            )
            _dest, was_reused = publish_sizing_envelope(envelope, evidence_root=evidence_root)
            reused += int(was_reused)
            published += int(not was_reused)
        coinalyze = project_coinalyze(
            evidence=coinalyze_evidence,
            supported=supported,
            unmapped=unmapped,
            lifecycles=lifecycles,
            identities=identities,
            staging=stage,
        )
        anchors = prove_coinalyze_anchor_identity(
            authority,
            identities=identities,
            retained_provider_symbols=coinalyze.retained_provider_symbols,
        )
        for envelope in sorted(stage.glob("coinalyze-*.parquet")):
            _dest, was_reused = publish_sizing_envelope(envelope, evidence_root=evidence_root)
            reused += int(was_reused)
            published += int(not was_reused)

    objects = tuple(selected) + tuple(cost)
    projections = project_families(measurements=measurements, objects=objects)
    normalized_family_bytes = sum(item.projected_bytes for item in projections)
    partition_count = (
        sum(item.partition_count for item in projections) + coinalyze.partition_count
    )
    membership_rows = len(
        list(dict(authority.report.get("membership") or {}).get("classifications") or ())
    )
    # The catalog charges the projected acquisition receipt set, not the five bounded
    # qualification provenance records.
    projected_receipts = coinalyze.inventory_receipts + coinalyze.liquidation_receipts
    catalog_pages = (
        len(objects) + partition_count + len(unmapped) + membership_rows + projected_receipts
    )
    catalog_bytes = (
        catalog_pages * CATALOG_PAGE_BYTES
        + ACCEPTED_REPORT_BYTES
        + ACCEPTED_MANIFEST_DETAIL_BYTES
    )
    normalized_catalog = (
        normalized_family_bytes + coinalyze.projected_normalized_bytes + catalog_bytes
    )
    largest_partition = max(
        max((item.largest_partition_bytes for item in projections), default=0),
        coinalyze.largest_partition_bytes,
    )
    high_water = normalized_catalog + max(
        ACCEPTED_LARGEST_SELECTED_OBJECT_BYTES, largest_partition
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
        "normalized_catalog_bytes": normalized_catalog,
        "temporary_high_water_bytes": high_water,
        "operating_reserve_bytes": reserve,
    }
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
        "measurements": [item.to_dict() for item in measurements],
        "projections": {
            "row_batch_cap": SIZING_ROW_BATCH,
            "writer_identity": writer_identity(),
            "arithmetic": "integer cross multiplication and ceiling division only",
            "families": [item.to_dict() for item in projections],
            "normalized_family_bytes": normalized_family_bytes,
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
            "projected_coinalyze_receipts": projected_receipts,
            "retained_coinalyze_evidence_records": len(coinalyze_evidence),
            "sizing_envelopes": len(measurements) + len(coinalyze.envelopes),
            "catalog_pages": catalog_pages,
            "count_sources": {
                "physical_raw_objects": "manifest detail rows plus accepted cost keys",
                "projected_normalized_files": "symbol-month groups times multiplicity",
                "typed_gap_rows": "report coinalyze universe_support.unmapped_symbols",
                "membership_rows": "report membership.classifications",
                "projected_coinalyze_receipts": (
                    "one liquidation receipt per supported mapping plus one inventory"
                ),
                "retained_coinalyze_evidence_records": "report coinalyze.provenance",
            },
        },
        "partitioning": {
            "rule": "one file per logical product, symbol, UTC month, and source family",
            "partition_count": partition_count,
            "catalog_page_bytes": CATALOG_PAGE_BYTES,
            "catalog_overhead_bytes": catalog_bytes,
            "largest_projected_partition_bytes": largest_partition,
            "largest_accepted_object_bytes": ACCEPTED_LARGEST_SELECTED_OBJECT_BYTES,
        },
        "capacity": {
            **components,
            "total_future_storage_bytes": sum(components.values()),
            "reserve_rule": "max(16 GiB, ceil(pre_write_available / 5)), never lowered",
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
        for name, value in sorted(components.items()):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                blockers.append(BLOCKER_UNKNOWN)
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
