"""Temporary completions exercise the real bundle preparer and catalog adapter."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
from decimal import Decimal
from dataclasses import replace
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.acquisition.binance_usdm_harmonic_sizing import final_product_schema

from cryptofactors.catalog.dataset.cex002_reference_release import (
    BITMEX_FALSE_AUTHORITY_TARGETS,
    QUARANTINE_MARKER,
    reference_proof_component,
)
from cryptofactors.catalog.dataset.cex002_reference_release import CODE_PATHS
from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.ingest.binance_usdm_harmonic_bundle import (
    ALIGNED_DAY_ROWS,
    BUNDLE_FIELDS,
    COST_SOURCE_GAP_BYTES,
    COST_SOURCE_GAP_ROWS,
    COST_SOURCE_GAP_SHA256,
    CURRENT_PLUS_FUTURE_PROVISION_BYTES,
    FEE_AUTHORITY_GAP_ROWS,
    FULL_CADENCE_DAY_COUNT,
    FULL_CADENCE_DAY_SHA256,
    HARMONIC_BUNDLE_ALLOCATION_BYTES,
    HOLDOUT_ID,
    HOLDOUT_UTC,
    MEASURED_CURRENT_BUNDLE_BYTES,
    OBSERVED_DAY_COUNT,
    OBSERVED_DAY_SHA256,
    OPERATING_RESERVE_BYTES,
    PRODUCTS,
    QUALITY_GAP_SCHEMA,
    RELEASE_METADATA_BYTES,
    RELEASE_METADATA_REMAINDER_BYTES,
    SIZING_PROJECTED_BUNDLE_ROWS,
    SOURCE_GAP_SCHEMA,
    TICKER_ACTUAL_ROWS,
    TICKER_EXCESS_ROWS,
    TICKER_PROJECTED_ROWS,
    TYPED_GAP_SCHEMA,
    UNUSED_COVERAGE_RESERVATION_BYTES,
    AssemblyPolicy,
    ReleaseError,
    _retained_kline_inventory,
    prepare_harmonic_bundle,
    release_metadata_budget,
)

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO / "sql/migrations"
COMMIT = "c" * 40
SIZING_CODE = "ab" * 32
SIZING_CLI = "cd" * 32
CHECKER = "d" * 64
NAUTILUS = "nautilus-test"
CONFIGURATION = {
    "failed_reconciliation_report_sha256": (
        "809d7d5338985fb0625a823ff8908eea"
        "b2c77e9406e5979d2fb8702cd17dfe10"
    ),
    "holdout_boundary_id": (
        "c842f813839e1dda375b351da0f693c5"
        "4bcf932e33eb6e3394aba860c12346e2"
    ),
    "holdout_sha256": (
        "2030e20aa5bd73df8fdbb7467e928508"
        "103b2e23659b85527101ec8b8546cb85"
    ),
    "holdout_utc": "2026-08-21T16:19:08.994166+00:00",
    "qualification_cli_sha256": (
        "473185ca946dcc37d506d8891e8f9557"
        "08ff80c976a586967762c1294956d28f"
    ),
    "qualification_code_sha256": (
        "2f88ad6e7cfc531fefe3d9c7a9ddbc83"
        "0741687e93c51450fc826062dffb2c74"
    ),
    "qualification_manifest_detail_sha256": (
        "64d0f74b8e4696c98d0f96423185fd96"
        "1aba6c63348d12425e3ec364b888f113"
    ),
    "qualification_report_sha256": (
        "f27b2ba7e6eff3a8b1385d985c49ee64"
        "ef60a394737b1246130d0f37b9015f09"
    ),
    "reconciliation_completion_sha256": (
        "e3c8f9f5ade1b92069b97e6b83931c34"
        "5886d40901b85b1c4106604edd9b5e5c"
    ),
    "reconciliation_report_sha256": (
        "96ae8db169666598643ac4e2f9aa2136"
        "b77c0dbeeaa90d2a3e4e4de9e983c89c"
    ),
    "sizing_sha256": (
        "3995a5072a7d84baecae677ceff6e1c7"
        "af9dd076daadec04a31717ffc8f16589"
    ),
}
SCENARIO = {
    "authority_class": "ASSUMED_CONSERVATIVE",
    "charges_each_side": True,
    "gap_kind": "historical_fee_schedule_unavailable",
    "historical_observation": False,
    "historical_upper_bound": False,
    "missing_fee_is_zero": False,
    "policy_known_at": "2026-08-23T03:00:00Z",
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


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _pretty(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _compact(value: object) -> bytes:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return (rendered + "\n").encode()


def _write(repo: Path, relative: str, payload: bytes) -> tuple[str, int]:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha(payload), len(payload)


def _contract(schema: pa.Schema) -> list[dict[str, object]]:
    return [
        {"name": field.name, "arrow_type": str(field.type), "nullable": bool(field.nullable)}
        for field in schema
    ]


def _write_parquet(schema: pa.Schema, count: int) -> bytes:
    arrays = []
    for field in schema:
        if count == 0:
            arrays.append(pa.array([], type=field.type))
            continue
        if pa.types.is_dictionary(field.type) or pa.types.is_string(field.type):
            arrays.append(pa.array(["BTCUSDT"] * count, type=field.type))
        elif pa.types.is_integer(field.type):
            arrays.append(pa.array(list(range(count)), type=field.type))
        elif pa.types.is_boolean(field.type):
            arrays.append(pa.array([False] * count, type=field.type))
        elif pa.types.is_floating(field.type):
            arrays.append(pa.array([0.0] * count, type=field.type))
        elif pa.types.is_decimal(field.type):
            arrays.append(pa.array([Decimal("1")] * count, type=field.type))
        elif pa.types.is_timestamp(field.type):
            arrays.append(pa.array([1_700_000_000_000_000_001] * count, type=field.type))
        elif pa.types.is_list(field.type):
            arrays.append(pa.array([[] for _ in range(count)], type=field.type))
        else:
            arrays.append(pa.array([None] * count, type=field.type))
    sink = pa.BufferOutputStream()
    pq.write_table(
        pa.Table.from_arrays(arrays, schema=schema),
        sink,
        compression="zstd",
        compression_level=3,
        version="2.6",
        row_group_size=65_536,
        use_dictionary=True,
        write_statistics=False,
        store_schema=True,
    )
    return sink.getvalue().to_pybytes()


def _empty(schema: pa.Schema) -> bytes:
    return _write_parquet(schema, 0)


def _partition(
    repo: Path,
    root: str,
    name: str,
    schema: pa.Schema,
    count: int,
    month: str | None,
    lineage_extra: dict | None = None,
) -> dict:
    parquet = _write_parquet(schema, count)
    digest, size = _write(repo, f"{root}/{name}.parquet", parquet)
    document: dict = {"row_count": count}
    if lineage_extra is None:
        document["mappings"] = [{"upstream": "fixture"}]
    else:
        document.update(lineage_extra)
        if document.get("parquet_sha256") == "FILL":
            document["parquet_sha256"] = digest
    lineage_payload = json.dumps(document).encode()
    lineage, lineage_size = _write(repo, f"{root}/{name}.lineage.json", lineage_payload)
    row = {
        "native_symbol": "BTCUSDT",
        "row_count": count,
        "parquet_path": f"{name}.parquet",
        "parquet_sha256": digest,
        "parquet_bytes": size,
        "lineage_path": f"{name}.lineage.json",
        "lineage_sha256": lineage,
        "lineage_bytes": lineage_size,
    }
    if month is not None:
        row["utc_month"] = month
    return row


def _global_quality(repo: Path, root: str, schema: pa.Schema) -> dict:
    payload = _empty(schema)
    digest, size = _write(repo, f"{root}/.quality-gaps/gap.parquet", payload)
    target = f".quality-gaps/{digest}.parquet"
    _write(repo, f"{root}/{target}", payload)
    (repo / root / ".quality-gaps/gap.parquet").unlink()
    lineage_document = {"row_count": 0, "component": "quality_gap"}
    lineage_payload = json.dumps(lineage_document).encode()
    lineage = _sha(lineage_payload)
    lineage_target = f".quality-gap-lineage/{lineage}.json"
    _write(repo, f"{root}/{lineage_target}", lineage_payload)
    return {
        "row_count": 0,
        "parquet_path": target,
        "parquet_sha256": digest,
        "parquet_bytes": size,
        "lineage_path": lineage_target,
        "lineage_sha256": lineage,
        "lineage_bytes": len(lineage_payload),
    }


def _placed_gap(
    repo: Path,
    root: str,
    kind: str,
    symbol: str | None,
    month: str | None,
    schema: pa.Schema,
    count: int,
) -> dict:
    payload = _write_parquet(schema, count)
    digest = _sha(payload)
    if symbol is None:
        parquet_rel = f".authority-gaps/{digest}.parquet"
        lineage_rel_root = ".authority-gap-lineage"
        lineage_document = {
            "row_count": count,
            "gap_kind": kind,
            "parquet_sha256": digest,
            "raw_objects": [{"name": "unmapped"}],
        }
    else:
        parquet_rel = f".quality-gaps/{symbol}/{month}/{digest}.parquet"
        lineage_rel_root = f".quality-gap-lineage/{symbol}/{month}"
        lineage_document = {
            "native_symbol": symbol,
            "utc_month": month,
            "parquet_sha256": digest,
            "row_count": count,
            "raw_objects": [{"name": "fixture"}],
            "gap_kind": kind,
        }
    _write(repo, f"{root}/{parquet_rel}", payload)
    lineage_payload = json.dumps(lineage_document).encode()
    lineage = _sha(lineage_payload)
    lineage_rel = f"{lineage_rel_root}/{lineage}.json"
    _write(repo, f"{root}/{lineage_rel}", lineage_payload)
    return {
        "kind": kind,
        "row_count": count,
        "parquet_path": parquet_rel,
        "parquet_sha256": digest,
        "parquet_bytes": len(payload),
        "lineage_path": lineage_rel,
        "lineage_sha256": lineage,
        "lineage_bytes": len(lineage_payload),
    }


def _completion(repo: Path, root: str, document: dict) -> str:
    payload = json.dumps(document).encode()
    digest = _sha(payload)
    _write(repo, f"{root}/.complete/{digest}.json", payload)
    return digest


def _manifest(repo: Path, root: str, name: str, rows: list[dict]) -> dict[str, object]:
    payload = json.dumps(
        {
            "document_type": f"binance_usdm_coverage_{name}_manifest",
            "schema_version": 1,
            "row_count": len(rows),
            "rows": rows,
        }
    ).encode()
    digest, size = _write(repo, f"{root}/.manifests/{_sha(payload)}.json", payload)
    return {"sha256": digest, "bytes": size, "path": f".manifests/{digest}.json"}


def _build(repo: Path) -> int:
    ordinary = pa.schema(
        [pa.field("native_symbol", pa.dictionary(pa.int32(), pa.string()), nullable=False)]
    )
    bundle_rows = 0
    completions: dict[str, str] = {}
    for spec in PRODUCTS:
        if spec.family in {"cost", "coverage"}:
            continue
        count = 1
        product_schema = final_product_schema(spec.dataset_type) if spec.dataset_type == "binance_usdm_mark_index_basis_1h" else ordinary
        month = None if spec.family == "membership" else "2024-01"
        lineage_extra = None
        if spec.family == "membership":
            lineage_extra = {"evidence_records": 4, "native_symbol": "BTCUSDT"}
        elif spec.dataset_type in {"binance_usdm_bar_1h", "binance_usdm_trade_flow_1h"}:
            lineage_extra = {
                "schema_version": 2,
                "native_symbol": "BTCUSDT",
                "utc_month": "2024-01",
                "parquet_sha256": "FILL",
                "raw_objects": [{"name": "current"}],
            }
        elif spec.dataset_type == "binance_usdm_open_interest_5m":
            lineage_extra = {
                "native_symbol": "BTCUSDT",
                "utc_month": "2024-01",
                "parquet_sha256": "FILL",
                "raw_objects": [{"name": "open-interest"}],
            }
        part = _partition(repo, spec.root, "part", product_schema, count, month, lineage_extra)
        document: dict = {
            "document_type": f"{spec.dataset_type}_product_completion",
            "schema_version": 1,
            "required_product": spec.dataset_type,
            "schema_sha256": _sha(
                _pretty({"required_product": spec.dataset_type, "schema": _contract(product_schema)})
            ),
            "partitions": [part],
        }
        if spec.family == "membership":
            document["membership_rows"] = count
            document["row_equation"] = {
                "classifications": count + 1,
                "accepted_membership_rows": count,
                "excluded_classifications": 1,
            }
        elif spec.dataset_type == "binance_usdm_open_interest_5m":
            document["quality_gap_artifact"] = _global_quality(repo, spec.root, QUALITY_GAP_SCHEMA)
            document["totals"] = {
                "physical_source_rows": count,
                "product_rows": count,
                "excluded_source_rows": 0,
                "collapsed_identical_source_rows": 0,
                "quality_gap_rows": 0,
            }
            bundle_rows += 1
        elif spec.dataset_type == "binance_usdm_funding_realized":
            document["row_equation"] = {
                "physical_source_rows": count,
                "collapsed_identical_rows": 0,
                "excluded_source_rows": 0,
                "inferred_events": 0,
                "conflicting_events": 0,
                "product_rows": count,
            }
        elif spec.dataset_type in {"binance_usdm_funding_indicative_1h", "binance_usdm_mark_index_basis_1h"}:
            legs = 3 if spec.dataset_type == "binance_usdm_mark_index_basis_1h" else 1
            document["row_equation"] = {
                "physical_source_rows": legs * count,
                "joined_input_rows": legs * count,
                "unjoinable_source_rows": 0,
                "excluded_source_rows": 0,
                "collapsed_identical_rows": 0,
                "fabricated_rows": 0,
                "product_rows": count,
            }
        elif spec.family == "partition":
            document["row_equation"] = {
                "physical_rows": count,
                "excluded_rows": 0,
                "product_rows": count,
            }
            if spec.dataset_type in {"binance_usdm_bar_1h", "binance_usdm_trade_flow_1h"}:
                document["quality_gap_artifact"] = _global_quality(repo, spec.root, QUALITY_GAP_SCHEMA)
                bundle_rows += 1
        elif spec.family == "liquidation":
            document["row_equation"] = {
                "physical_source_rows": count,
                "collapsed_identical_rows": 0,
                "product_rows": count,
                "missing_daily_slots": 0,
                "inclusive_requested_slots": count,
            }
            document["gaps"] = [
                _placed_gap(repo, spec.root, "quality_gap", "BTCUSDT", "2024-01", ordinary, 0),
                _placed_gap(repo, spec.root, "coinalyze_symbol_unmapped", None, None, ordinary, 1),
            ]
            bundle_rows += 2
        completions[spec.dataset_type] = _completion(repo, spec.root, document)
        bundle_rows += 1
    cost_schema = pa.schema([pa.field("value", pa.int64(), nullable=False)])
    cost_contract = _contract(cost_schema)
    counts = {
        "retained_book_ticker": 5,
        "retained_book_depth": 1,
        "official_fee_schedule": 0,
        "fee_authority_gap": 1,
        "scenario_policy": 2,
    }
    partitions = []
    identities = {}
    for component, count in counts.items():
        part = _partition(repo, "data/.cex002_cost_calibration", component, cost_schema, count, "2024-01")
        part["component"] = component
        partitions.append(part)
        identities[component] = _sha(
            _pretty(
                {
                    "required_product": "binance_usdm_cost_calibration",
                    "component": component,
                    "schema": cost_contract,
                }
            )
        )
        bundle_rows += 1
    frozen_payload = b'{"document_type":"frozen_source_gaps"}\n'
    frozen_sha, frozen_size = _write(
        repo,
        "data/.cex002_cost_calibration/.source-gaps/pending.json",
        frozen_payload,
    )
    frozen_relative = f".source-gaps/{frozen_sha}.json"
    _write(repo, f"data/.cex002_cost_calibration/{frozen_relative}", frozen_payload)
    (repo / "data/.cex002_cost_calibration/.source-gaps/pending.json").unlink()
    cost_schema_body = {key: cost_contract for key in counts}
    completions["binance_usdm_cost_calibration"] = _completion(
        repo,
        "data/.cex002_cost_calibration",
        {
            "document_type": "binance_usdm_cost_calibration_product_completion",
            "schema_version": 1,
            "required_product": "binance_usdm_cost_calibration",
            "schema_sha256": _sha(
                _pretty({"required_product": "binance_usdm_cost_calibration", "schema": cost_schema_body})
            ),
            "component_schemas": identities,
            "partitions": partitions,
            "ticker_row_projection_disposition": {
                "projected_rows": 2,
                "actual_rows": 5,
                "excess_rows": 3,
                "status": "EXCEEDED_REVIEWED_EXACT_ARTIFACT_VARIANCE",
                "ordinary_sizing_check_passed": False,
            },
            "encoded_validation_scope": {
                "independent_complete_csv_to_parquet_value_equality_claimed": False
            },
            "fee_authority": {"missing_fee_is_zero": False},
            "scenario_policy": {"historical_observation": False},
            "frozen_source_gaps": {
                "path": frozen_relative,
                "sha256": frozen_sha,
                "bytes": frozen_size,
                "row_count": 1,
            },
        },
    )
    coverage_root = "data/.cex002_coverage"
    gap_schemas = {
        "source_gap": SOURCE_GAP_SCHEMA,
        "typed_gap": TYPED_GAP_SCHEMA,
        "quality_gap": QUALITY_GAP_SCHEMA,
    }
    pages = {}
    gap_rows = {}
    for name, schema in gap_schemas.items():
        payload = _empty(schema)
        folder = {"source_gap": "source-gaps", "typed_gap": "typed-gaps", "quality_gap": "quality-gaps"}[name]
        month = "authority" if name in {"source_gap", "typed_gap"} else "2024-01"
        digest, size = _write(repo, f"{coverage_root}/pending-{name}.parquet", payload)
        lineage_payload = json.dumps({
            "upstream": [{"upstream": "fixture"}], "row_count": 0,
            "component": folder,
            "required_product": "binance_usdm_bar_1h",
            "native_symbol": "BTCUSDT", "utc_month": month,
            "parquet_sha256": digest,
        }).encode()
        lineage, lineage_size = _write(repo, f"{coverage_root}/pending-{name}.json", lineage_payload)
        target = f".{folder}/binance_usdm_bar_1h/BTCUSDT/{month}/{digest}.parquet"
        lineage_target = f".{folder}-lineage/binance_usdm_bar_1h/BTCUSDT/{month}/{lineage}.json"
        _write(repo, f"{coverage_root}/{target}", payload)
        _write(repo, f"{coverage_root}/{lineage_target}", lineage_payload)
        (repo / coverage_root / f"pending-{name}.parquet").unlink()
        (repo / coverage_root / f"pending-{name}.json").unlink()
        row = {
            "required_product": "binance_usdm_bar_1h",
            "native_symbol": "BTCUSDT",
            "row_count": 0,
            "parquet_sha256": digest,
            "parquet_bytes": size,
            "lineage_sha256": lineage,
            "lineage_bytes": lineage_size,
        }
        if name == "quality_gap":
            row["utc_month"] = month
        gap_rows[name] = row
        bundle_rows += 1
    daily_payload = b'{"document_type":"daily"}\n'
    daily_sha, daily_size = _write(repo, f"{coverage_root}/.daily/BTCUSDT/2024-01/pending.json", daily_payload)
    daily_named = f".daily/BTCUSDT/2024-01/{daily_sha}.json"
    _write(repo, f"{coverage_root}/{daily_named}", daily_payload)
    pending_daily = repo / coverage_root / ".daily/BTCUSDT/2024-01/pending.json"
    pending_daily.unlink()
    summary_payload = b'{"document_type":"summary"}\n'
    summary_sha, summary_size = _write(
        repo,
        f"{coverage_root}/.summary/BTCUSDT/pending.json",
        summary_payload,
    )
    summary_named = f".summary/BTCUSDT/{summary_sha}.json"
    _write(repo, f"{coverage_root}/{summary_named}", summary_payload)
    (repo / coverage_root / ".summary/BTCUSDT/pending.json").unlink()
    pages["source_gap"] = _manifest(repo, coverage_root, "source_gap", [gap_rows["source_gap"]])
    pages["typed_gap"] = _manifest(repo, coverage_root, "typed_gap", [gap_rows["typed_gap"]])
    pages["quality_gap"] = _manifest(repo, coverage_root, "quality_gap", [gap_rows["quality_gap"]])
    pages["daily"] = _manifest(
        repo,
        coverage_root,
        "daily",
        [
            {
                "native_symbol": "BTCUSDT",
                "utc_month": "2024-01",
                "sha256": daily_sha,
                "bytes": daily_size,
            }
        ],
    )
    pages["summary"] = _manifest(
        repo,
        coverage_root,
        "summary",
        [{"native_symbol": "BTCUSDT", "sha256": summary_sha, "bytes": summary_size}],
    )
    pages["excluded_membership"] = _manifest(
        repo,
        coverage_root,
        "excluded_membership",
        [{"native_symbol": "OLDUSDT"}],
    )
    source_contract = _contract(SOURCE_GAP_SCHEMA)
    source_schema = _sha(
        _pretty({"required_product": "binance_usdm_coverage_gap", "schema": source_contract})
    )
    completions["binance_usdm_coverage_gap"] = _completion(
        repo,
        coverage_root,
        {
            "document_type": "binance_usdm_coverage_gap_product_completion",
            "schema_version": 1,
            "required_product": "binance_usdm_coverage_gap",
            "publication": {"visible_harmonic_bundle": False},
            "alignment": {
                "five_product_observed_day_count": 428_090,
                "five_product_observed_day_sha256": OBSERVED_DAY_SHA256,
                "full_cadence_day_count": 424_431,
                "full_cadence_day_sha256": FULL_CADENCE_DAY_SHA256,
                "aligned_day_rows": 1_971_447,
                "funding_expected_count": None,
                "liquidation_complete": False,
            },
            "metadata_ledger": {
                "release_wide_allocation_bytes": 5_556_368_003,
                "reserved_debit_bytes": 570_896_384,
                "reserved_release_remainder_bytes": 4_985_471_619,
                "unused_coverage_reservation_reallocatable": False,
                "measured_coverage_reservation_remaining_bytes": 114_144_134,
            },
            "components": {
                "source_gap": {"rows": 0, "schema_sha256": source_schema},
                "typed_gap_membership": {
                    "rows": 0,
                    "schema_sha256": _sha(_compact(_contract(TYPED_GAP_SCHEMA))),
                },
                "quality_gap": {
                    "rows": 0,
                    "schema_sha256": _sha(_compact(_contract(QUALITY_GAP_SCHEMA))),
                },
                "fee_authority_gap_reference": {"rows": 771, "copied": False},
                "cost_normalization_source_gap_reference": {
                    "rows": 1,
                    "sha256": frozen_sha,
                    "bytes": frozen_size,
                    "copied": False,
                },
            },
            "manifests": pages,
        },
    )
    _write(
        repo,
        "research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json",
        b'{"kind":"fixture"}\n',
    )
    _write(
        repo,
        "data/cex002_qualify/cex002_holdout_boundary.json",
        json.dumps({"boundary_id": HOLDOUT_ID, "boundary_utc": HOLDOUT_UTC}).encode(),
    )
    report = {
        "document_type": "cex002_bounded_kline_reconciliation_report",
        "status": "PASS",
        "coverage": {
            "matched_field_count": 2672,
            "field_denominator": 2672,
            "successfully_compared_hour_count": 167,
            "distinct_day_count": 9,
            "logical_role_count": 10,
            "roles_with_compared_hour": 10,
        },
        "discrepancies": [],
        "coverage_failures": [],
        "unexplained_absences": [],
    }
    report_payload = json.dumps(report).encode()
    report_sha = _sha(report_payload)
    _write(
        repo,
        f"data/.cex002_kline_reconciliation/.reports/{report_sha}.json",
        report_payload,
    )
    recon = {
        "document_type": "cex002_bounded_kline_reconciliation_completion",
        "status": "PASS",
        "report_sha256": report_sha,
        "bar_completion_sha256": completions["binance_usdm_bar_1h"],
        "flow_completion_sha256": completions["binance_usdm_trade_flow_1h"],
        "qualification_report_sha256": _sha(b'{"kind":"fixture"}\n'),
    }
    recon_payload = json.dumps(recon).encode()
    _write(repo, f"data/.cex002_kline_reconciliation/.complete/{_sha(recon_payload)}.json", recon_payload)
    bundle_contract = [
        {"name": name, "arrow_type": arrow, "nullable": nullable} for name, arrow, nullable in BUNDLE_FIELDS
    ]
    sizing = {
        "code_identity": {"sizing_source_sha256": SIZING_CODE, "sizing_cli_sha256": SIZING_CLI},
        "capacity": {
            "operating_reserve_bytes": 29_690_701_415,
            "catalog_manifest_bundle_bytes": 5_556_368_003,
        },
        "projections": {
            "fixed_schema_products": {
                "binance_usdm_harmonic_bundle": {
                    "projected_bytes": 1_133_590,
                    "projected_rows": 150_331,
                }
            }
        },
        "partitioning": {
            "largest_future_width_charge_candidates": {"harmonic_bundle": 24_352_003},
            "largest_future_width_charge_inputs": {
                "bundle_rows": 150_331,
                "reference_index_bytes_per_row": 8,
                "bundle_reference_dictionary_bytes": 299_043,
            },
        },
        "typed_schema_contract": {
            "non_archive_product_schemas": {"binance_usdm_harmonic_bundle": bundle_contract}
        },
    }
    _write(
        repo,
        "research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json",
        json.dumps(sizing).encode(),
    )
    return bundle_rows


def _policy(repo: Path, catalog: Path, production: bool = False) -> AssemblyPolicy:
    return AssemblyPolicy(
        repo=repo,
        catalog_path=catalog,
        code_commit=COMMIT,
        bind_runtime=False,
        file_bytes={
            relative: f"fixture-{index}".encode() for index, relative in enumerate(CODE_PATHS)
        },
        authenticate_production_receipt=production,
        observed_free_bytes=OPERATING_RESERVE_BYTES + 8_000_000_000,
    )


def _seed(catalog: Path) -> None:
    connection = sqlite3.connect(catalog)
    try:
        for target in BITMEX_FALSE_AUTHORITY_TARGETS:
            connection.execute(
                """
                INSERT INTO dataset (
                    dataset_id, dataset_type, schema_version, manifest_sha256, manifest_uri,
                    transform_name, transform_version, code_commit, config_sha256, row_count,
                    byte_size, quality_status, quality_summary_json, publication_status, created_at
                ) VALUES (?, ?, '1', ?, ?, 'cex002_reference_publication', '1', ?, ?, ?, ?,
                          'REJECTED', ?, 'REGISTERED', ?)
                """,
                (
                    target.dataset_id,
                    target.dataset_type,
                    target.manifest_sha256,
                    f"bitmex/manifests/{target.dataset_id}.json",
                    COMMIT,
                    "e" * 64,
                    target.rows,
                    target.byte_size,
                    json.dumps({"quarantine_marker": QUARANTINE_MARKER}),
                    target.created_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO dataset_file (
                    dataset_id, storage_uri, file_sha256, byte_size, row_count, partition_json
                ) VALUES (?, ?, ?, ?, ?, '{}')
                """,
                (
                    target.dataset_id,
                    target.relative_path,
                    target.file_sha256,
                    target.byte_size,
                    target.rows,
                ),
            )
        connection.commit()
    finally:
        connection.close()


def _fixture(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    catalog = tmp_path / "catalog.sqlite"
    apply_migrations(catalog, MIGRATIONS)
    rows = _build(repo)
    return repo, catalog, _policy(repo, catalog), rows


def _retained_kline_files(repo: Path, product: str) -> dict[str, bytes]:
    spec = next(item for item in PRODUCTS if item.dataset_type == product)
    completion_path = next((repo / spec.root / ".complete").glob("*.json"))
    accepted = json.loads(completion_path.read_bytes())["partitions"][0]
    current = json.loads((repo / spec.root / accepted["lineage_path"]).read_bytes())
    assert current["schema_version"] == 2
    schema = pq.ParquetFile(repo / spec.root / accepted["parquet_path"]).schema_arrow
    old_parquet = _write_parquet(schema, 2)
    old_parquet_path = f"{spec.root}/.partitions/BTCUSDT/2024-01/{_sha(old_parquet)}.parquet"
    _write(repo, old_parquet_path, old_parquet)
    old_lineage = json.dumps({
        "schema_version": 1,
        "required_product": product,
        "native_symbol": "BTCUSDT",
        "utc_month": "2024-01",
        "row_count": 1,
        "parquet_sha256": accepted["parquet_sha256"],
        "raw_objects": [{"name": "older-unreferenced"}],
    }, sort_keys=True).encode()
    old_lineage_path = f"{spec.root}/.lineage/BTCUSDT/2024-01/{_sha(old_lineage)}.json"
    _write(repo, old_lineage_path, old_lineage)
    return {old_parquet_path: old_parquet, old_lineage_path: old_lineage}


def test_release_pins_and_metadata_budget() -> None:
    assert [spec.root for spec in PRODUCTS] == [
        "data/.cex002_perpetual_membership",
        "data/.cex002_bar_1h",
        "data/.cex002_trade_flow_1h",
        "data/.cex002_open_interest_5m",
        "data/.cex002_funding_realized",
        "data/.cex002_price_state/binance_usdm_funding_indicative_1h",
        "data/.cex002_price_state/binance_usdm_mark_index_basis_1h",
        "data/.cex002_liquidation_observed_daily",
        "data/.cex002_cost_calibration",
        "data/.cex002_coverage",
    ]
    assert MEASURED_CURRENT_BUNDLE_BYTES == 1_133_590
    assert SIZING_PROJECTED_BUNDLE_ROWS == 150_331
    assert HARMONIC_BUNDLE_ALLOCATION_BYTES == 24_352_003
    measured_plus_cap = MEASURED_CURRENT_BUNDLE_BYTES + HARMONIC_BUNDLE_ALLOCATION_BYTES
    assert measured_plus_cap == 25_485_593
    assert CURRENT_PLUS_FUTURE_PROVISION_BYTES == 25_485_593
    assert SIZING_PROJECTED_BUNDLE_ROWS * 8 + 22_850_312 + 299_043 == 24_352_003
    assert RELEASE_METADATA_BYTES == 5_556_368_003
    remainder = release_metadata_budget(UNUSED_COVERAGE_RESERVATION_BYTES)
    assert remainder == RELEASE_METADATA_REMAINDER_BYTES
    assert release_metadata_budget(114_144_134) == 4_985_471_619
    assert release_metadata_budget(114_144_134) != 4_985_471_619 + 114_144_134
    ticker_excess = TICKER_ACTUAL_ROWS - TICKER_PROJECTED_ROWS
    assert ticker_excess == TICKER_EXCESS_ROWS == 136_532_583
    assert (TICKER_PROJECTED_ROWS, TICKER_ACTUAL_ROWS) == (745_543_507, 882_076_090)
    assert OBSERVED_DAY_COUNT == 428_090
    assert OBSERVED_DAY_SHA256 == (
        "f0c0d7c21fc68d2d454b07ec969b6d79"
        "4f380e22e751c643dee09184e3896665"
    )
    assert FULL_CADENCE_DAY_COUNT == 424_431
    assert FULL_CADENCE_DAY_SHA256 == (
        "22219a5a243fcf1fda3ab5deacd99fbe"
        "72869375021d9d2f2a98868580e48fab"
    )
    assert ALIGNED_DAY_ROWS == 1_971_447
    assert FEE_AUTHORITY_GAP_ROWS == 771
    assert (COST_SOURCE_GAP_ROWS, COST_SOURCE_GAP_BYTES) == (494, 178_783)
    assert COST_SOURCE_GAP_SHA256 == (
        "aace941a43e38c2f790fed4c383e08cb"
        "bd27d3f5f7215bc95b50bb134ae3519e"
    )
    assert OPERATING_RESERVE_BYTES == 29_690_701_415
    assert [name for name, _arrow, _nullable in BUNDLE_FIELDS] == [
        "required_product",
        "component",
        "dataset_id",
        "native_symbol",
        "canonical_instrument_id",
        "canonical_instrument_version_id",
        "reference_identity_state",
        "utc_month",
        "partition_sha256",
        "partition_bytes",
        "row_count",
        "schema_sha256",
        "lineage_manifest_sha256",
        "lineage_mapping_count",
        "source_report_sha256",
        "source_manifest_detail_sha256",
        "qualification_code_sha256",
        "qualification_cli_sha256",
        "sizing_code_sha256",
        "sizing_cli_sha256",
        "configuration_sha256",
        "scenario_policy_sha256",
        "unit_convention",
        "censorship_semantics",
        "coverage_gap_rows",
        "typed_gap_membership_rows",
        "fee_authority_gap_rows",
        "cross_product_intersection_count",
        "cross_product_intersection_sha256",
    ]


def test_prepare_preserves_economics_and_accounts_every_file(tmp_path: Path) -> None:
    repo, _catalog, policy, rows = _fixture(tmp_path)
    prepared = prepare_harmonic_bundle(policy)
    assert prepared.consumable is False
    assert rows != 150_331
    bundle = next(item for item in prepared.manifests if item.dataset_type == "binance_usdm_harmonic_bundle")
    table = pq.ParquetFile(repo / bundle.files[0].relative_path).read()
    assert table.num_rows == rows
    assert bundle.files[0].bytes <= 24_352_003
    frame = table.to_pylist()
    assert {row["cross_product_intersection_count"] for row in frame} == {428_090}
    assert {row["cross_product_intersection_sha256"] for row in frame} == {OBSERVED_DAY_SHA256}
    assert {row["fee_authority_gap_rows"] for row in frame} == {771}
    assert {row["canonical_instrument_id"] for row in frame} == {None}
    assert {row["sizing_code_sha256"] for row in frame} == {SIZING_CODE}
    assert {row["configuration_sha256"] for row in frame} == {_sha(_pretty(CONFIGURATION))}
    assert {row["scenario_policy_sha256"] for row in frame} == {_sha(_pretty(SCENARIO))}
    membership = next(row for row in frame if row["required_product"] == "binance_usdm_perpetual_membership")
    assert membership["utc_month"] == "absent"
    assert membership["lineage_mapping_count"] == 4
    bar_gap = next(
        row
        for row in frame
        if row["required_product"] == "binance_usdm_bar_1h"
        and row["component"] == "quality_gap"
        and row["dataset_id"] == prepared.dataset_ids["binance_usdm_bar_1h"]
    )
    assert bar_gap["native_symbol"] == "absent"
    assert bar_gap["utc_month"] == "absent"
    coverage_quality = next(
        row for row in frame
        if row["required_product"] == "binance_usdm_bar_1h"
        and row["component"] == "quality_gap"
        and row["dataset_id"] == prepared.dataset_ids["binance_usdm_coverage_gap"]
    )
    assert coverage_quality["native_symbol"] == "BTCUSDT"
    oi = next(
        row
        for row in frame
        if row["required_product"] == "binance_usdm_open_interest_5m" and row["component"] == ""
    )
    assert oi["lineage_mapping_count"] == 1
    assert oi["native_symbol"] == "BTCUSDT"
    authority = next(row for row in frame if row["component"] == "coinalyze_symbol_unmapped")
    assert authority["native_symbol"] == "absent"
    assert authority["utc_month"] == "absent"
    assert authority["required_product"] == "binance_usdm_liquidation_observed_daily"
    fee = next(row for row in frame if row["component"] == "official_fee_schedule")
    assert fee["row_count"] == 0
    ticker = next(row for row in frame if row["component"] == "retained_book_ticker")
    assert ticker["row_count"] == 5
    coverage = next(item for item in prepared.manifests if item.dataset_type == "binance_usdm_coverage_gap")
    gap = next(row for row in frame if row["component"] == "source_gap")
    assert gap["required_product"] == "binance_usdm_bar_1h"
    assert gap["dataset_id"] == coverage.dataset_id
    assert gap["utc_month"] == "authority"
    assert coverage.quality_summary["intersections"]["full_cadence_day_count"] == 424_431
    assert coverage.quality_summary["fee_authority_gap_reference"]["copied"] is False
    cost = next(item for item in prepared.manifests if item.dataset_type == "binance_usdm_cost_calibration")
    disposition = cost.quality_summary["ticker_row_projection_disposition"]
    assert disposition["ordinary_sizing_check_passed"] is False
    assert disposition["excess_rows"] == disposition["actual_rows"] - disposition["projected_rows"]
    assert cost.quality_summary["frozen_source_gaps"]["copied"] is False
    frozen = [spec for spec in cost.files if spec.partition.get("role") == "frozen_source_gaps"]
    assert len(frozen) == 1
    assert frozen[0].partition["kind"] == "metadata"
    assert frozen[0].rows == 0
    assert all(row["required_product"] != "binance_usdm_harmonic_bundle" for row in frame)
    descriptor = json.loads((repo / prepared.descriptor_relative_path).read_text())
    assert descriptor["consumable"] is False
    assert descriptor["catalog_commit_required"] is True
    resources = descriptor["authorities"]["resources"]
    assert resources["operating_reserve_spent"] is False
    assert resources["measured_current_bundle_bytes"] == 1_133_590
    assert resources["sizing_projected_bundle_rows"] == 150_331
    assert resources["harmonic_bundle_allocation_bytes"] == 24_352_003
    assert resources["current_plus_future_provision_bytes"] == 25_485_593
    assert resources["release_metadata_pool_bytes"] == 5_556_368_003
    assert resources["reconstructed_bundle_rows"] == rows
    assert resources["bundle_rows"] == rows
    assert resources["bundle_file_bytes"] <= 24_352_003
    assert resources["bundle_file_bytes"] != 1_133_590
    assert "publication_sha256" not in json.dumps(cost.quality_summary)
    owned = repo / "data/.cex002_harmonic_bundle"
    def inventory() -> dict[str, tuple[str, int, int, int]]:
        return {
            path.relative_to(owned).as_posix():
                (_sha(path.read_bytes()), path.stat().st_size, path.stat().st_ino, path.stat().st_mtime_ns)
            for path in owned.rglob("*") if path.is_file()
        }
    before = inventory()
    replay = prepare_harmonic_bundle(policy)
    assert replay.descriptor_sha256 == prepared.descriptor_sha256
    assert inventory() == before
    assert not [path for path in owned.rglob("*.tmp") if path.is_file()]


def test_retained_kline_inventory_is_audited_outside_accepted_datasets(tmp_path: Path) -> None:
    repo, _catalog, policy, expected_rows = _fixture(tmp_path)
    baseline = prepare_harmonic_bundle(policy)
    retained = {}
    for product in ("binance_usdm_bar_1h", "binance_usdm_trade_flow_1h"):
        retained[product] = _retained_kline_files(repo, product)
    prepared = prepare_harmonic_bundle(policy)
    assert prepared.dataset_ids == baseline.dataset_ids
    assert prepared.descriptor_sha256 != baseline.descriptor_sha256
    assert prepared.bundle_bytes == baseline.bundle_bytes
    descriptor = json.loads((repo / prepared.descriptor_relative_path).read_bytes())
    audit = descriptor["authorities"]["retained_unreferenced_kline_inventory"]
    referenced = {item.relative_path for manifest in prepared.manifests for item in manifest.files}
    for product, files in retained.items():
        assert not (set(files) & referenced)
        ordered = sorted(files)
        independent = b"".join(_compact({
            "kind": "parquet" if path.endswith(".parquet") else "lineage",
            "path": path, "sha256": _sha(files[path]), "bytes": len(files[path]),
        }) for path in ordered)
        assert audit[product] == {
            "parquet_count": 1,
            "parquet_bytes": sum(len(body) for path, body in files.items() if path.endswith(".parquet")),
            "lineage_count": 1,
            "lineage_bytes": sum(len(body) for path, body in files.items() if path.endswith(".json")),
            "inventory_sha256": _sha(independent),
        }
    bundle = next(item for item in prepared.manifests if item.dataset_type == "binance_usdm_harmonic_bundle")
    assert pq.ParquetFile(repo / bundle.files[0].relative_path).metadata.num_rows == expected_rows
    assert prepare_harmonic_bundle(policy).descriptor_sha256 == prepared.descriptor_sha256
    assert all((repo / path).read_bytes() == body for files in retained.values() for path, body in files.items())


@pytest.mark.parametrize("defect", ["hash", "path", "symlink", "class"])
def test_retained_kline_rejects_unsafe_or_unknown_files(tmp_path: Path, defect: str) -> None:
    repo, _catalog, policy, _rows = _fixture(tmp_path)
    files = _retained_kline_files(repo, "binance_usdm_bar_1h")
    lineage_path = next(path for path in files if path.endswith(".json"))
    if defect == "hash":
        (repo / lineage_path).write_bytes(files[lineage_path] + b" ")
    elif defect == "path":
        _write(repo, "data/.cex002_bar_1h/.lineage/BTCUSDT/2024-13/" + _sha(b"old") + ".json", b"old")
    elif defect == "symlink":
        (repo / "data/.cex002_bar_1h/.lineage/BTCUSDT/2024-01" / (_sha(b"link") + ".json")).symlink_to(
            repo / lineage_path
        )
    else:
        (repo / "data/.cex002_bar_1h/unknown.txt").write_bytes(b"unknown")
    with pytest.raises(ReleaseError) as error:
        prepare_harmonic_bundle(policy)
    assert error.value.blocker in {"unsafe_path", "reference_mismatch"}


def test_retained_kline_production_count_and_missing_accepted_file(tmp_path: Path) -> None:
    repo, _catalog, policy, _rows = _fixture(tmp_path)
    files = _retained_kline_files(repo, "binance_usdm_trade_flow_1h")
    spec = next(item for item in PRODUCTS if item.dataset_type == "binance_usdm_trade_flow_1h")
    extras = {path[len(spec.root) + 1:] for path in files}
    with pytest.raises(ReleaseError) as count:
        _retained_kline_inventory(repo, spec, extras, production=True)
    assert count.value.blocker == "reference_mismatch"
    completion = json.loads(next((repo / spec.root / ".complete").glob("*.json")).read_bytes())
    (repo / spec.root / completion["partitions"][0]["parquet_path"]).unlink()
    with pytest.raises(ReleaseError) as missing:
        prepare_harmonic_bundle(policy)
    assert missing.value.blocker == "reference_mismatch"


def test_cli_reports_blocker_product_and_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo, catalog, policy, _rows = _fixture(tmp_path)
    unknown = repo / "data/.cex002_perpetual_membership/unexpected.txt"
    unknown.write_bytes(b"unexpected")
    assert _cli().main(
        ["prepare", "--repo", str(repo), "--catalog", str(catalog), "--code-commit", COMMIT],
        policy=policy,
    ) == 1
    error = capsys.readouterr().err
    assert "reference_mismatch" in error
    assert "binance_usdm_perpetual_membership" in error
    assert str(unknown.relative_to(repo)) in error


def test_unsafe_extra_and_production_pin_failures(tmp_path: Path) -> None:
    repo, catalog, policy, _rows = _fixture(tmp_path)
    stray = repo / "data/.cex002_bar_1h/stray.txt"
    stray.write_text("extra\n")
    with pytest.raises(ReleaseError) as extra:
        prepare_harmonic_bundle(policy)
    assert extra.value.blocker == "reference_mismatch"
    stray.unlink()
    completion = next((repo / "data/.cex002_bar_1h/.complete").iterdir())
    document = json.loads(completion.read_text())
    document["partitions"][0]["parquet_path"] = "../escape.parquet"
    payload = json.dumps(document).encode()
    completion.unlink()
    escaped = repo / "data/.cex002_bar_1h/.complete" / f"{_sha(payload)}.json"
    escaped.write_bytes(payload)
    with pytest.raises(ReleaseError) as unsafe:
        prepare_harmonic_bundle(policy)
    assert unsafe.value.blocker == "unsafe_path"
    fresh, _catalog, fresh_policy, _rows = _fixture(tmp_path / "production")
    with pytest.raises(ReleaseError) as pinned:
        production = replace(fresh_policy, authenticate_production_receipt=True)
        prepare_harmonic_bundle(production)
    assert pinned.value.blocker == "identity_pin"
    assert fresh.is_dir()
    assert catalog.is_file()


def _cli():
    path = REPO / "scripts/research/publish_binance_usdm_harmonic_bundle.py"
    spec = importlib.util.spec_from_file_location(
        "publish_binance_usdm_harmonic_bundle",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _proof(repo: Path, prepared) -> bytes:
    datasets = []
    for manifest in prepared.manifests:
        components = []
        for spec in manifest.files:
            components.append(
                reference_proof_component(
                    repo / spec.relative_path,
                    spec.relative_path,
                    spec.partition["kind"],
                )
            )
        datasets.append({"dataset_id": manifest.dataset_id, "components": components})
    document = {
        "document_type": "cex002_harmonic_bundle_consumer_proof",
        "schema_version": 1,
        "status": "PASS",
        "scope": "complete_release",
        "candidate_sha256": prepared.descriptor_sha256,
        "checker_source_sha256": CHECKER,
        "nautilus_version": NAUTILUS,
        "datasets": datasets,
    }
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode()


def test_cli_prepare_publish_and_verify(tmp_path: Path) -> None:
    cli = _cli()
    assert cli.main([]) == 2
    repo, catalog, policy, _rows = _fixture(tmp_path)
    _seed(catalog)
    assert (
        cli.main(
            ["prepare", "--repo", str(repo), "--catalog", str(catalog), "--code-commit", COMMIT],
            policy=policy,
        )
        == 0
    )
    prepared_path = next((repo / "data/.cex002_harmonic_bundle/.prepared").glob("*.json"))
    prepared_sha = prepared_path.stem
    document = json.loads(prepared_path.read_text())
    assert document["consumable"] is False
    prepared = prepare_harmonic_bundle(policy)
    assert prepared.descriptor_sha256 == prepared_sha
    proof = tmp_path / "proof.json"
    proof_bytes = _proof(repo, prepared)
    proof.write_bytes(proof_bytes)
    proof_sha = _sha(proof_bytes)
    assert (
        cli.main(
            [
                "publish",
                "--repo",
                str(repo),
                "--catalog",
                str(catalog),
                "--code-commit",
                COMMIT,
                "--prepared-sha",
                prepared_sha,
                "--proof",
                str(proof),
                "--proof-sha",
                proof_sha,
                "--checker-sha",
                CHECKER,
                "--nautilus-version",
                NAUTILUS,
            ],
            policy=policy,
        )
        == 0
    )
    publication = next((repo / "data/.cex002_harmonic_bundle/.publication").glob("*.json"))
    assert (
        cli.main(
            [
                "verify",
                "--repo",
                str(repo),
                "--catalog",
                str(catalog),
                "--code-commit",
                COMMIT,
                "--publication-sha",
                publication.stem,
                "--proof",
                str(proof),
                "--proof-sha",
                proof_sha,
                "--checker-sha",
                CHECKER,
                "--nautilus-version",
                NAUTILUS,
            ],
            policy=policy,
        )
        == 0
    )
    connection = sqlite3.connect(catalog)
    try:
        visible = connection.execute(
            "SELECT COUNT(*) FROM dataset WHERE dataset_type = 'binance_usdm_harmonic_bundle'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert visible == 1
