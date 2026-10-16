from __future__ import annotations

import hashlib
import json
import os
import threading
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.acquisition import binance_usdm_harmonic_sizing as sizing
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    PRODUCT_BAR_1H,
    PRODUCT_FUNDING_INDICATIVE_1H,
    PRODUCT_FUNDING_REALIZED,
    PRODUCT_LIQUIDATION_OBSERVED_DAILY,
    PRODUCT_MARK_INDEX_BASIS_1H,
    PRODUCT_OPEN_INTEREST_5M,
    PRODUCT_TRADE_FLOW_1H,
    cost_component_columns,
    final_product_schema,
)
from cryptofactors.ingest import binance_usdm_coverage as coverage


def _ms(day: int, hour: int = 0, minute: int = 0) -> int:
    return int(datetime(2025, 9, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


def _member(symbol: str = "0GUSDT") -> dict[str, Any]:
    return {"symbol": symbol, "evidence": [{"onboard_ms": _ms(17), "closed_observed_ms": None}]}


def _timestamps(days: range, count: int, spacing_minutes: int) -> list[int]:
    return [_ms(day) + offset * spacing_minutes * 60_000 for day in days for offset in range(count)]


def _write_timestamp_partition(
    tmp_path: Path,
    product: str,
    values: list[int],
    *,
    column_name: str | None = None,
) -> coverage.PartitionInput:
    field = column_name or coverage.TIMESTAMP_COLUMNS[product]
    path = tmp_path / f"{product}.parquet"
    schema = pa.schema([pa.field(field, pa.int64(), nullable=False)])
    pq.write_table(pa.Table.from_pydict({field: values}, schema=schema), path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return coverage.PartitionInput(product, "0GUSDT", "2025-09", len(values), path, digest, path, digest, digest)


def _product(tmp_path: Path, product: str, schema: pa.Schema) -> coverage.ProductInput:
    completion: dict[str, Any] = {"partitions": [], "gaps": [], "frozen_source_gaps": {"sha256": "a" * 64}}
    return coverage.ProductInput(product, tmp_path, tmp_path, completion, tmp_path / "completion.json", "b" * 64, schema)


def _alignment_fixture(tmp_path: Path) -> tuple[dict[str, coverage.ProductInput], dict[str, dict[tuple[str, str], coverage.PartitionInput]]]:
    bar = _timestamps(range(18, 31), 24, 60) + [_ms(17, hour) for hour in range(15, 24)]
    oi = _timestamps(range(18, 31), 288, 5) + [_ms(17) + offset * 300_000 for offset in range(189, 288)]
    funding = [_ms(17, 8), _ms(17, 16)]
    funding += [_ms(day) + offset * 4 * 3_600_000 for day in range(18, 22) for offset in range(6)]
    funding += [_ms(22) + offset * 3_600_000 for offset in range(15)]
    funding += _timestamps(range(23, 31), 24, 60)
    basis = [_ms(22, hour) for hour in range(10, 24)] + _timestamps(range(23, 31), 24, 60)
    liquidation = [_ms(day, 12) for day in range(17, 31)]
    values = {
        PRODUCT_BAR_1H: bar,
        PRODUCT_OPEN_INTEREST_5M: oi,
        PRODUCT_FUNDING_REALIZED: funding,
        PRODUCT_MARK_INDEX_BASIS_1H: basis,
        PRODUCT_LIQUIDATION_OBSERVED_DAILY: liquidation,
    }
    products: dict[str, coverage.ProductInput] = {}
    index: dict[str, dict[tuple[str, str], coverage.PartitionInput]] = {}
    for product, timestamps in values.items():
        part = _write_timestamp_partition(tmp_path, product, timestamps)
        products[product] = _product(tmp_path, product, pa.schema([pa.field(coverage.TIMESTAMP_COLUMNS[product], pa.int64(), nullable=False)]))
        index[product] = {("0GUSDT", "2025-09"): part}
    for product in (PRODUCT_TRADE_FLOW_1H, PRODUCT_FUNDING_INDICATIVE_1H):
        products[product] = _product(tmp_path, product, pa.schema([pa.field(coverage.TIMESTAMP_COLUMNS[product], pa.int64(), nullable=False)]))
        index[product] = {}
    products["binance_usdm_cost_calibration"] = _product(tmp_path, "binance_usdm_cost_calibration", pa.schema([]))
    return products, index


def _read_published_json(root: Path, directory: str, digest: str) -> dict[str, Any]:
    return json.loads((root / directory / f"{digest}.json").read_text())


def test_frozen_gap_schemas_and_allocations_are_exact() -> None:
    assert coverage.SOURCE_GAP_SCHEMA == final_product_schema("binance_usdm_coverage_gap")
    assert len(coverage.SOURCE_GAP_SCHEMA) == 23
    assert len(coverage.TYPED_GAP_SCHEMA) == 6
    assert len(coverage.QUALITY_GAP_SCHEMA) == 12
    assert (coverage.SOURCE_GAP_ROWS, coverage.SOURCE_GAP_PARTITIONS, coverage.SOURCE_GAP_BYTES) == (8_317, 4_817, 36_831_146)
    assert (coverage.TYPED_GAP_ROWS, coverage.TYPED_GAP_PARTITIONS, coverage.TYPED_GAP_BYTES) == (3_742, 3_742, 7_757_166)
    assert (coverage.QUALITY_GAP_ROWS, coverage.QUALITY_GAP_PARTITIONS, coverage.QUALITY_GAP_BYTES) == (216_934_972, 130_820, 9_154_761_060)
    assert (coverage.SOURCE_GAP_LARGEST_FILE, coverage.TYPED_GAP_LARGEST_FILE, coverage.QUALITY_GAP_LARGEST_FILE) == (9_458, 2_073, 418_609)


def test_shared_metadata_ledger_is_debited_once() -> None:
    assert sum(coverage.METADATA_PAGE_COUNTS.values()) == 139_379
    assert 139_379 * coverage.METADATA_PAGE_BYTES == coverage.METADATA_BUDGET_BYTES == 570_896_384
    assert coverage.RELEASE_METADATA_BYTES - coverage.METADATA_BUDGET_BYTES == coverage.RELEASE_METADATA_REMAINDER_BYTES == 4_985_471_619


def test_native_identity_keeps_canonical_reference_explicitly_null() -> None:
    row = coverage.native_identity("0GUSDT")
    assert row["native_symbol"] == "0GUSDT"
    assert row["canonical_instrument_id"] is None
    assert row["canonical_instrument_version_id"] is None
    assert row["reference_identity_state"] == "reference_identity_not_yet_created"


def test_membership_and_exclusion_classes_cover_the_complete_report() -> None:
    assert 698 + 73 == coverage.ACCEPTED_MEMBERSHIP_IDENTITIES == 771
    assert 771 + coverage.ACCEPTED_REJECTED_MEMBERSHIP_ROWS == 1_008


def test_funding_only_membership_still_gets_the_complete_daily_matrix(tmp_path: Path) -> None:
    products, index = _alignment_fixture(tmp_path)
    tree = coverage._OutputTree(tmp_path / ".coverage", coverage.PublicationHooks())
    try:
        reports, summaries, totals = coverage.publish_reports(
            tree,
            products=products,
            index=index,
            membership=[_member(), _member("FUNDINGONLYUSDT")],
            typed_rows=[],
            source_rows=[
                {
                    "required_product": PRODUCT_BAR_1H,
                    "native_symbol": "0GUSDT",
                    "first_observed_period": "2025-09",
                    "last_observed_period": "2025-09",
                }
            ],
            quality_missing_counts={},
        )
    finally:
        tree.close()
    assert len(reports) == len(summaries) == 2
    assert totals["daily_report_equation"] == {
        "accepted_membership_identities": 2,
        "historical_utc_months": 1,
        "expected_partitions": 2,
        "published_partitions": 2,
    }
    funding_only = next(row for row in reports if row["native_symbol"] == "FUNDINGONLYUSDT")
    document = _read_published_json(tmp_path / ".coverage", ".daily/FUNDINGONLYUSDT/2025-09", funding_only["sha256"])
    assert all(day[1] == [0, 0, 0, 0, 0] for day in document["days"])


@pytest.mark.parametrize("value", ["", ".", "..", "a/b", "a\\b", "a\x00b"])
def test_unsafe_output_components_are_refused(value: str) -> None:
    with pytest.raises(coverage.CoverageNormalizationError):
        coverage._safe_component(value, "fixture")


@pytest.mark.parametrize("value", ["/absolute", "../escape", "a/../../escape", "./local"])
def test_unsafe_descriptor_paths_are_refused(value: str) -> None:
    with pytest.raises(coverage.CoverageNormalizationError):
        coverage._safe_relative(value, "fixture")


def test_pinned_json_refuses_hash_mismatch_and_symlink(tmp_path: Path) -> None:
    target = tmp_path / "authority.json"
    target.write_text("{}\n")
    with pytest.raises(coverage.CoverageNormalizationError, match="digest"):
        coverage._read_json(target, "0" * 64)
    link = tmp_path / "linked.json"
    link.symlink_to(target)
    with pytest.raises(coverage.CoverageNormalizationError, match="symlink"):
        coverage._read_json(link, hashlib.sha256(target.read_bytes()).hexdigest())


def test_partition_refuses_wrong_schema_hash_and_lineage(tmp_path: Path) -> None:
    product = PRODUCT_BAR_1H
    schema = final_product_schema(product)
    parquet_path = tmp_path / "part.parquet"
    pq.write_table(pa.Table.from_pylist([], schema=schema), parquet_path)
    lineage_path = tmp_path / "lineage.json"
    lineage_path.write_text(json.dumps({"required_product": product, "native_symbol": "0GUSDT", "utc_month": "2025-09", "row_count": 0}, sort_keys=True, separators=(",", ":")) + "\n")
    descriptor = {
        "native_symbol": "0GUSDT",
        "utc_month": "2025-09",
        "row_count": 0,
        "parquet_path": parquet_path.name,
        "parquet_sha256": "0" * 64,
        "lineage_path": lineage_path.name,
        "lineage_sha256": hashlib.sha256(lineage_path.read_bytes()).hexdigest(),
    }
    item = coverage.ProductInput(product, tmp_path, tmp_path, {}, tmp_path / "c", "a" * 64, schema)
    with pytest.raises(coverage.CoverageNormalizationError, match="Parquet digest"):
        coverage.validate_partition(item, descriptor)


def test_partition_refuses_wrong_schema_and_wrong_lineage_hash(tmp_path: Path) -> None:
    product = PRODUCT_BAR_1H
    parquet_path = tmp_path / "part.parquet"
    pq.write_table(pa.table({"open_time": pa.array([], type=pa.int64())}), parquet_path)
    parquet_sha = hashlib.sha256(parquet_path.read_bytes()).hexdigest()
    lineage_path = tmp_path / "lineage.json"
    lineage_path.write_text(json.dumps({"required_product": product, "native_symbol": "0GUSDT", "utc_month": "2025-09", "row_count": 0}, sort_keys=True, separators=(",", ":")) + "\n")
    descriptor = {"native_symbol": "0GUSDT", "utc_month": "2025-09", "row_count": 0, "parquet_path": parquet_path.name, "parquet_sha256": parquet_sha, "lineage_path": lineage_path.name, "lineage_sha256": "0" * 64}
    item = coverage.ProductInput(product, tmp_path, tmp_path, {}, tmp_path / "c", "a" * 64, final_product_schema(product))
    with pytest.raises(coverage.CoverageNormalizationError, match="lineage digest"):
        coverage.validate_partition(item, descriptor)
    descriptor["lineage_sha256"] = hashlib.sha256(lineage_path.read_bytes()).hexdigest()
    with pytest.raises(coverage.CoverageNormalizationError, match="schema"):
        coverage.validate_partition(item, descriptor)


def test_authenticated_partition_scan_refuses_parent_substitution(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    original = _write_timestamp_partition(source, PRODUCT_BAR_1H, [_ms(1)])
    moved = tmp_path / "moved"
    source.rename(moved)
    source.mkdir()
    _write_timestamp_partition(source, PRODUCT_BAR_1H, [_ms(2)])
    rebound = coverage.PartitionInput(
        original.product,
        original.native_symbol,
        original.utc_month,
        original.row_count,
        source / original.parquet_path.name,
        original.parquet_sha256,
        original.lineage_path,
        original.lineage_sha256,
        original.descriptor_sha256,
    )
    with pytest.raises(coverage.CoverageNormalizationError, match="changed before timestamp scan"):
        coverage._scan_partition(
            rebound,
            pa.schema([pa.field("open_time", pa.int64(), nullable=False)]),
        )


def test_oi_uses_create_time_and_retains_nonzero_native_phase(tmp_path: Path) -> None:
    assert coverage.TIMESTAMP_COLUMNS[PRODUCT_OPEN_INTEREST_5M] == "create_time"
    phase = 1_234
    values = [_ms(1) + phase + offset * 300_000 for offset in range(288)]
    good = _write_timestamp_partition(
        tmp_path,
        PRODUCT_OPEN_INTEREST_5M,
        values,
        column_name="create_time",
    )
    schema = pa.schema([pa.field("create_time", pa.int64(), nullable=False)])
    scan = coverage._scan_partition(good, schema)
    assert scan.observed_by_day == Counter({"2025-09-01": 288})
    assert scan.cadence_complete_by_day["2025-09-01"] is True
    assert (scan.first_observed_ms, scan.last_observed_ms, scan.duplicate_timestamps) == (
        values[0],
        values[-1],
        0,
    )


@pytest.mark.parametrize("interval_ms", [301_000, 599_000])
def test_oi_irregular_intervals_are_observed_without_invented_gaps(tmp_path: Path, interval_ms: int) -> None:
    # Stay below 1,000 ms so the 599-second shift keeps the final row in this UTC day.
    phase = 500
    values = [_ms(1) + phase + offset * 300_000 for offset in range(288)]
    values[100:] = [value + interval_ms - 300_000 for value in values[100:]]
    irregular = _write_timestamp_partition(
        tmp_path,
        PRODUCT_OPEN_INTEREST_5M,
        values,
        column_name="create_time",
    )
    schema = pa.schema([pa.field("create_time", pa.int64(), nullable=False)])
    scan = coverage._scan_partition(irregular, schema)
    assert scan.observed_by_day["2025-09-01"] == 288
    assert scan.distinct_by_day["2025-09-01"] == 288
    assert scan.cadence_complete_by_day["2025-09-01"] is False
    assert scan.cadence_failure_by_day["2025-09-01"] == "irregular_native_interval"
    assert values[100] - values[99] == interval_ms


def test_oi_utc_month_boundary_is_independent_of_native_phase(tmp_path: Path) -> None:
    schema = pa.schema([pa.field("create_time", pa.int64(), nullable=False)])
    spill = _write_timestamp_partition(
        tmp_path,
        PRODUCT_OPEN_INTEREST_5M,
        [int(datetime(2025, 10, 1, tzinfo=UTC).timestamp() * 1000) + 1_234],
        column_name="create_time",
    )
    with pytest.raises(coverage.CoverageNormalizationError, match="descriptor month"):
        coverage._scan_partition(spill, schema)


def test_variable_interval_funding_never_gets_an_expected_grid(tmp_path: Path) -> None:
    products, index = _alignment_fixture(tmp_path)
    tree = coverage._OutputTree(tmp_path / ".coverage", coverage.PublicationHooks())
    try:
        _, summaries, totals = coverage.publish_reports(tree, products=products, index=index, membership=[_member()], typed_rows=[], source_rows=[{"required_product": PRODUCT_FUNDING_REALIZED, "native_symbol": "0GUSDT", "first_observed_period": "2025-09", "last_observed_period": "2025-09"}], quality_missing_counts={})
    finally:
        tree.close()
    summary = _read_published_json(tmp_path / ".coverage", ".summary/0GUSDT", summaries[0]["sha256"])
    funding = next(row for row in summary["products"] if row["required_product"] == PRODUCT_FUNDING_REALIZED)
    assert funding["observed_count"] == 233
    assert funding["expected_count"] is None
    assert funding["expected_count_basis"] is None
    assert totals["maximum_loaded_symbol_month_observations"] == 3_843


def test_common_symbol_month_does_not_prove_common_days(tmp_path: Path) -> None:
    products, index = _alignment_fixture(tmp_path)
    tree = coverage._OutputTree(tmp_path / ".coverage", coverage.PublicationHooks())
    try:
        reports, _, totals = coverage.publish_reports(tree, products=products, index=index, membership=[_member()], typed_rows=[], source_rows=[{"required_product": PRODUCT_BAR_1H, "native_symbol": "0GUSDT", "first_observed_period": "2025-09", "last_observed_period": "2025-09"}], quality_missing_counts={})
    finally:
        tree.close()
    assert all(("0GUSDT", "2025-09") in index[product] for product in coverage.ALIGNMENT_PRODUCTS)
    assert totals["five_product_observed_day_count"] == 9
    assert totals["full_cadence_day_count"] == 8
    document = _read_published_json(tmp_path / ".coverage", ".daily/0GUSDT/2025-09", reports[0]["sha256"])
    row_22 = next(row for row in document["days"] if row[0] == "2025-09-22")
    row_23 = next(row for row in document["days"] if row[0] == "2025-09-23")
    assert row_22[-2:] == [True, False]
    assert row_22[1][3] == 14 and row_22[3][3] is False
    assert document["exclusion_reason_dictionary"][str(row_22[4][3])].startswith(
        "partial_fixed_cadence_day"
    )
    assert row_23[-2:] == [True, True]


def test_duplicate_timestamp_cannot_conceal_a_missing_fixed_slot(tmp_path: Path) -> None:
    values = [_ms(1, hour) for hour in range(23)] + [_ms(1, 22)]
    part = _write_timestamp_partition(tmp_path, PRODUCT_BAR_1H, values)
    scan = coverage._scan_partition(
        part,
        pa.schema([pa.field("open_time", pa.int64(), nullable=False)]),
    )
    assert scan.observed_by_day["2025-09-01"] == 24
    assert scan.distinct_by_day["2025-09-01"] == 23
    assert scan.cadence_complete_by_day["2025-09-01"] is False
    assert scan.cadence_failure_by_day["2025-09-01"] == "duplicate_and_missing_native_slots"


def test_zero_valued_liquidation_row_is_present_while_an_absent_day_is_missing(tmp_path: Path) -> None:
    products, index = _alignment_fixture(tmp_path)
    schema = final_product_schema(PRODUCT_LIQUIDATION_OBSERVED_DAILY)
    row = {
        **coverage.native_identity("0GUSDT"),
        "raw_object_ref": 0,
        "point_ordinal": 0,
        "provider_symbol": "0G",
        "event_time_ms": _ms(23, 12),
        "long_liquidation": Decimal("0"),
        "short_liquidation": Decimal("0"),
        "liquidation_imbalance": Decimal("0"),
        "source_interval_seconds": 86_400,
        "observation_semantics": "observed_censored_daily_point",
        "event_complete": False,
    }
    path = tmp_path / "liquidation-zero.parquet"
    pq.write_table(pa.Table.from_pylist([row], schema=schema), path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    index[PRODUCT_LIQUIDATION_OBSERVED_DAILY][("0GUSDT", "2025-09")] = coverage.PartitionInput(
        PRODUCT_LIQUIDATION_OBSERVED_DAILY,
        "0GUSDT",
        "2025-09",
        1,
        path,
        digest,
        path,
        digest,
        digest,
    )
    products[PRODUCT_LIQUIDATION_OBSERVED_DAILY] = _product(
        tmp_path,
        PRODUCT_LIQUIDATION_OBSERVED_DAILY,
        schema,
    )
    tree = coverage._OutputTree(tmp_path / ".coverage", coverage.PublicationHooks())
    try:
        reports, _, totals = coverage.publish_reports(tree, products=products, index=index, membership=[_member()], typed_rows=[], source_rows=[{"required_product": PRODUCT_BAR_1H, "native_symbol": "0GUSDT", "first_observed_period": "2025-09", "last_observed_period": "2025-09"}], quality_missing_counts={})
    finally:
        tree.close()
    document = _read_published_json(tmp_path / ".coverage", ".daily/0GUSDT/2025-09", reports[0]["sha256"])
    observed = next(item for item in document["days"] if item[0] == "2025-09-23")
    missing = next(item for item in document["days"] if item[0] == "2025-09-22")
    assert observed[1][4] == 1 and observed[2][4] is True and observed[4][4] is None
    assert missing[1][4] == 0 and missing[2][4] is False
    assert "not_zero" in document["exclusion_reason_dictionary"][str(missing[4][4])]
    assert totals["five_product_observed_day_count"] == 1


def test_whole_liquidation_partition_absence_keeps_availability_unknown(tmp_path: Path) -> None:
    products, index = _alignment_fixture(tmp_path)
    index[PRODUCT_LIQUIDATION_OBSERVED_DAILY].clear()
    tree = coverage._OutputTree(tmp_path / ".coverage", coverage.PublicationHooks())
    try:
        reports, _, _ = coverage.publish_reports(
            tree,
            products=products,
            index=index,
            membership=[_member()],
            typed_rows=[],
            source_rows=[{"required_product": PRODUCT_BAR_1H, "native_symbol": "0GUSDT"}],
            quality_missing_counts={},
        )
    finally:
        tree.close()
    document = _read_published_json(tmp_path / ".coverage", ".daily/0GUSDT/2025-09", reports[0]["sha256"])
    day = next(item for item in document["days"] if item[0] == "2025-09-23")
    assert document["exclusion_reason_dictionary"][str(day[4][4])] == (
        "no_accepted_partition_observation;source_availability_unknown"
    )


def test_source_gap_does_not_erase_an_observed_day(tmp_path: Path) -> None:
    products, index = _alignment_fixture(tmp_path)
    tree = coverage._OutputTree(tmp_path / ".coverage", coverage.PublicationHooks())
    source_gap = {"required_product": PRODUCT_BAR_1H, "native_symbol": "0GUSDT", "first_observed_period": "2025-09", "last_observed_period": "2025-09", "gap_kind": "head_gap_family_launch"}
    try:
        reports, summaries, _ = coverage.publish_reports(tree, products=products, index=index, membership=[_member()], typed_rows=[], source_rows=[source_gap], quality_missing_counts={})
    finally:
        tree.close()
    daily = _read_published_json(tmp_path / ".coverage", ".daily/0GUSDT/2025-09", reports[0]["sha256"])
    observed = next(row for row in daily["days"] if row[0] == "2025-09-23")
    assert observed[2][0] is True
    summary = _read_published_json(tmp_path / ".coverage", ".summary/0GUSDT", summaries[0]["sha256"])
    bar = next(row for row in summary["products"] if row["required_product"] == PRODUCT_BAR_1H)
    assert bar["source_gap_row_sha256"]
    assert bar["qualification_source_gap_context"][0]["gap_kind"] == "head_gap_family_launch"
    assert bar["qualification_source_gap_context"][0]["semantics"] == "qualification_gap_context;not_a_current_missing_observation"


def test_unmatched_price_state_and_unknown_availability_are_explicit(tmp_path: Path) -> None:
    products, index = _alignment_fixture(tmp_path)
    index[PRODUCT_MARK_INDEX_BASIS_1H].clear()
    tree = coverage._OutputTree(tmp_path / ".coverage", coverage.PublicationHooks())
    try:
        reports, _, _ = coverage.publish_reports(
            tree,
            products=products,
            index=index,
            membership=[_member()],
            typed_rows=[{"required_product": PRODUCT_MARK_INDEX_BASIS_1H, "native_symbol": "0GUSDT"}],
            source_rows=[{"required_product": PRODUCT_BAR_1H, "native_symbol": "0GUSDT"}],
            quality_missing_counts={},
        )
    finally:
        tree.close()
    document = _read_published_json(tmp_path / ".coverage", ".daily/0GUSDT/2025-09", reports[0]["sha256"])
    row = next(item for item in document["days"] if item[0] == "2025-09-23")
    assert document["exclusion_reason_dictionary"][str(row[4][3])] == "typed_source_unavailable"
    assert row[3][3] is False and row[-2] is False
    assert document["semantics"]["availability"] == "unknown_not_a_causal_vintage"


def test_unknown_source_bounds_fall_back_to_actual_product_range(tmp_path: Path) -> None:
    products, index = _alignment_fixture(tmp_path)
    tree = coverage._OutputTree(tmp_path / ".coverage", coverage.PublicationHooks())
    try:
        _, _, totals = coverage.publish_reports(
            tree,
            products=products,
            index=index,
            membership=[_member()],
            typed_rows=[],
            source_rows=[{"required_product": PRODUCT_BAR_1H, "native_symbol": "0GUSDT", "onboard_period": "", "close_period": ""}],
            quality_missing_counts={},
        )
    finally:
        tree.close()
    assert totals["historical_domain"] == {
        "first_utc_month": "2025-09",
        "last_utc_month": "2025-09",
        "month_count": 1,
        "basis": "accepted_source_membership_bounds_and_actual_product_ranges",
    }


def test_fixed_cadence_expected_count_uses_observed_plus_quality_gaps(tmp_path: Path) -> None:
    products, index = _alignment_fixture(tmp_path)
    tree = coverage._OutputTree(tmp_path / ".coverage", coverage.PublicationHooks())
    try:
        _, summaries, _ = coverage.publish_reports(
            tree,
            products=products,
            index=index,
            membership=[_member()],
            typed_rows=[],
            source_rows=[
                {
                    "required_product": PRODUCT_BAR_1H,
                    "native_symbol": "0GUSDT",
                    "first_observed_period": "2025-09",
                    "last_observed_period": "2025-09",
                }
            ],
            quality_missing_counts={(PRODUCT_BAR_1H, "0GUSDT"): 7},
            quality_gap_references={
                (PRODUCT_BAR_1H, "0GUSDT"): [
                    {
                        "utc_month": "2025-09",
                        "row_count": 1,
                        "parquet_sha256": "a" * 64,
                        "lineage_sha256": "b" * 64,
                    }
                ]
            },
        )
    finally:
        tree.close()
    summary = _read_published_json(tmp_path / ".coverage", ".summary/0GUSDT", summaries[0]["sha256"])
    bar = next(row for row in summary["products"] if row["required_product"] == PRODUCT_BAR_1H)
    assert (bar["observed_count"], bar["missing_count"], bar["expected_count"]) == (321, 7, 328)
    assert bar["quality_gap_partitions"][0]["utc_month"] == "2025-09"


def test_cost_summary_uses_component_rows_and_authenticated_source_days(tmp_path: Path) -> None:
    products, index = _alignment_fixture(tmp_path)
    partitions: list[dict[str, Any]] = []
    for component, rows, source_day in (
        ("retained_book_depth", 7, "2025-09-17"),
        ("retained_book_ticker", 11, "2025-09-23"),
        ("fee_authority_gap", 1, None),
    ):
        parquet_sha = hashlib.sha256(component.encode()).hexdigest()
        lineage_document = {
            "component": component,
            "native_symbol": "0GUSDT",
            "row_count": rows,
            "parquet_sha256": parquet_sha,
            "raw_objects": [] if source_day is None else [{"economic_day": source_day}],
        }
        body = coverage._canonical_json(lineage_document)
        lineage = tmp_path / f"{component}.json"
        lineage.write_bytes(body)
        partitions.append(
            {
                "component": component,
                "native_symbol": "0GUSDT",
                "utc_month": "authority" if source_day is None else source_day[:7],
                "row_count": rows,
                "parquet_path": f"{component}.parquet",
                "parquet_sha256": parquet_sha,
                "parquet_bytes": 1,
                "lineage_path": lineage.name,
                "lineage_sha256": hashlib.sha256(body).hexdigest(),
                "lineage_bytes": len(body),
            }
        )
    cost = products["binance_usdm_cost_calibration"]
    products["binance_usdm_cost_calibration"] = coverage.ProductInput(
        cost.product,
        cost.root,
        cost.descriptor_root,
        {**cost.completion, "partitions": partitions},
        cost.completion_path,
        cost.completion_sha256,
        cost.schema,
    )
    tree = coverage._OutputTree(tmp_path / ".coverage", coverage.PublicationHooks())
    try:
        _, summaries, _ = coverage.publish_reports(
            tree,
            products=products,
            index=index,
            membership=[_member()],
            typed_rows=[],
            source_rows=[{"required_product": PRODUCT_BAR_1H, "native_symbol": "0GUSDT"}],
            quality_missing_counts={},
        )
    finally:
        tree.close()
    summary = _read_published_json(tmp_path / ".coverage", ".summary/0GUSDT", summaries[0]["sha256"])
    cost_row = next(
        row for row in summary["products"] if row["required_product"] == "binance_usdm_cost_calibration"
    )
    assert cost_row["observed_count"] is None
    assert cost_row["component_counts"] == [
        {"component": "fee_authority_gap", "row_count": 1, "unit": "authority_gap_rows"},
        {"component": "retained_book_depth", "row_count": 7, "unit": "normalized_book_depth_rows"},
        {"component": "retained_book_ticker", "row_count": 11, "unit": "normalized_book_ticker_rows"},
    ]
    assert cost_row["source_day_extrema"] == [
        {"component": "retained_book_depth", "first_source_day": "2025-09-17", "last_source_day": "2025-09-17"},
        {"component": "retained_book_ticker", "first_source_day": "2025-09-23", "last_source_day": "2025-09-23"},
    ]
    assert cost_row["first_observed_ms"] is None and cost_row["duplicate_timestamps"] is None


def test_hbar_checksum_quality_gap_keeps_inclusive_native_phase_endpoints(tmp_path: Path) -> None:
    row = {
        **coverage.native_identity("HBARUSDC"),
        "required_product": PRODUCT_OPEN_INTEREST_5M,
        "utc_month": "2026-07",
        "missing_run_start_ms": int(datetime(2026, 7, 9, tzinfo=UTC).timestamp() * 1000) + 1_234,
        "missing_run_end_ms": int(datetime(2026, 7, 9, 23, 55, tzinfo=UTC).timestamp() * 1000) + 1_234,
        "expected_grid_count": 288,
        "gap_kind": "provider_checksum_conflict",
        "reason": "provider checksum conflict remains unavailable",
    }
    parquet = tmp_path / "hbar.parquet"
    pq.write_table(pa.Table.from_pylist([row], schema=coverage.QUALITY_GAP_SCHEMA), parquet)
    parquet_sha = hashlib.sha256(parquet.read_bytes()).hexdigest()
    lineage = tmp_path / "hbar.json"
    lineage.write_text(json.dumps({"row_count": 1}, sort_keys=True, separators=(",", ":")) + "\n")
    lineage_sha = hashlib.sha256(lineage.read_bytes()).hexdigest()
    products = {
        name: _product(tmp_path, name, pa.schema([]))
        for name in coverage.TIMESTAMP_COLUMNS
    }
    products[PRODUCT_OPEN_INTEREST_5M] = coverage.ProductInput(
        PRODUCT_OPEN_INTEREST_5M,
        tmp_path,
        tmp_path,
        {"quality_gap_artifact": {"parquet_path": parquet.name, "parquet_sha256": parquet_sha, "lineage_path": lineage.name, "lineage_sha256": lineage_sha, "row_count": 1}},
        tmp_path / "completion.json",
        "c" * 64,
        pa.schema([]),
    )
    tree = coverage._OutputTree(tmp_path / ".coverage", coverage.PublicationHooks())
    try:
        manifest, totals, missing = coverage.publish_quality_gaps(tree, products, {"HBARUSDC"})
    finally:
        tree.close()
    assert totals["quality_gap_rows"] == 1
    assert missing[(PRODUCT_OPEN_INTEREST_5M, "HBARUSDC")] == 288
    output = tmp_path / ".coverage" / ".quality-gaps" / PRODUCT_OPEN_INTEREST_5M / "HBARUSDC" / "2026-07" / f"{manifest[0]['parquet_sha256']}.parquet"
    written = pq.read_table(output).to_pylist()[0]
    assert written["missing_run_start_ms"] % 300_000 == 1_234
    assert written["missing_run_end_ms"] % 300_000 == 1_234
    assert written["expected_grid_count"] == 288
    output_lineage = tmp_path / ".coverage" / ".quality-gaps-lineage" / PRODUCT_OPEN_INTEREST_5M / "HBARUSDC" / "2026-07" / f"{manifest[0]['lineage_sha256']}.json"
    upstream = json.loads(output_lineage.read_text())["upstream"][0]
    assert (upstream["first_source_row_ordinal"], upstream["last_source_row_ordinal"], upstream["source_row_count"]) == (0, 0, 1)


def _equation_product(product: str, value: Mapping[str, Any]) -> coverage.ProductInput:
    key = "totals" if product == PRODUCT_OPEN_INTEREST_5M else "row_equation"
    return coverage.ProductInput(product, Path("."), Path("."), {key: dict(value)}, Path("c"), "a" * 64, pa.schema([]))


def test_each_product_row_equation_is_reconciled_in_its_native_units() -> None:
    products = {
        PRODUCT_BAR_1H: _equation_product(PRODUCT_BAR_1H, {"physical_rows": 10, "product_rows": 9, "excluded_rows": 1, "collapsed_rows": 0, "duplicate_rows": 0, "overlap_rows": 0}),
        PRODUCT_TRADE_FLOW_1H: _equation_product(PRODUCT_TRADE_FLOW_1H, {"physical_rows": 10, "product_rows": 8, "excluded_rows": 2, "collapsed_rows": 0, "duplicate_rows": 0, "overlap_rows": 0}),
        PRODUCT_OPEN_INTEREST_5M: _equation_product(PRODUCT_OPEN_INTEREST_5M, {"physical_source_rows": 12, "product_rows": 9, "excluded_source_rows": 1, "collapsed_identical_source_rows": 2}),
        PRODUCT_FUNDING_REALIZED: _equation_product(PRODUCT_FUNDING_REALIZED, {"physical_source_rows": 8, "product_rows": 7, "excluded_source_rows": 0, "collapsed_identical_rows": 1, "inferred_events": 0, "conflicting_events": 0}),
        PRODUCT_FUNDING_INDICATIVE_1H: _equation_product(PRODUCT_FUNDING_INDICATIVE_1H, {"physical_source_rows": 8, "joined_input_rows": 7, "unjoinable_source_rows": 1, "excluded_source_rows": 0, "collapsed_identical_rows": 0, "product_rows": 7, "fabricated_rows": 0}),
        PRODUCT_MARK_INDEX_BASIS_1H: _equation_product(PRODUCT_MARK_INDEX_BASIS_1H, {"physical_source_rows": 22, "joined_input_rows": 21, "unjoinable_source_rows": 1, "excluded_source_rows": 0, "collapsed_identical_rows": 0, "product_rows": 7, "fabricated_rows": 0}),
        PRODUCT_LIQUIDATION_OBSERVED_DAILY: _equation_product(PRODUCT_LIQUIDATION_OBSERVED_DAILY, {"inclusive_requested_slots": 10, "product_rows": 7, "missing_daily_slots": 3, "physical_source_rows": 7, "excluded_source_rows": 0, "collapsed_identical_rows": 0, "imputed_rows": 0}),
        "binance_usdm_perpetual_membership": _equation_product("binance_usdm_perpetual_membership", {"classifications": 3, "accepted_membership_rows": 2, "excluded_classifications": 1}),
        "binance_usdm_cost_calibration": coverage.ProductInput(
            "binance_usdm_cost_calibration",
            Path("."),
            Path("."),
            {
                "source_equation": {
                    "objects": 12,
                    "generation0_objects": 10,
                    "recovery_objects": 2,
                    "physical_rows": 99,
                    "retained_rows": 99,
                    "deduplicated_rows": 0,
                    "dropped_rows": 0,
                },
                "fee_authority": {
                    "gap_rows": 771,
                    "official_historical_rows": 0,
                    "missing_fee_is_zero": False,
                },
                "scenario_policy": {"rows": 2, "historical_observation": False},
            },
            Path("c"),
            "a" * 64,
            pa.schema([]),
        ),
    }
    coverage.validate_row_equations(products)
    broken = dict(products)
    broken[PRODUCT_OPEN_INTEREST_5M] = _equation_product(PRODUCT_OPEN_INTEREST_5M, {"physical_source_rows": 13, "product_rows": 9, "excluded_source_rows": 1, "collapsed_identical_source_rows": 2})
    with pytest.raises(coverage.CoverageNormalizationError, match="open-interest"):
        coverage.validate_row_equations(broken)


def test_metadata_overrun_fails_before_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coverage, "METADATA_BUDGET_BYTES", 8)
    root = tmp_path / ".coverage"
    tree = coverage._OutputTree(root, coverage.PublicationHooks())
    try:
        with pytest.raises(coverage.CoverageNormalizationError, match="budget"):
            tree.publish_json({"too": "large"}, directory=".summary", kind="summary")
        assert not list((root / ".summary").glob("*.json")) if (root / ".summary").exists() else True
    finally:
        tree.close()


def test_interruption_never_publishes_completion(tmp_path: Path) -> None:
    def interrupt(kind: str, _temporary: Path, _final: Path) -> None:
        if kind == "completion":
            raise RuntimeError("interrupt")

    root = tmp_path / ".coverage"
    tree = coverage._OutputTree(root, coverage.PublicationHooks(before_publish=interrupt))
    try:
        with pytest.raises(RuntimeError, match="interrupt"):
            tree.publish(b"{}\n", directory=".complete", suffix="json", kind="completion", row_count=None, metadata=True)
        assert not list((root / ".complete").glob("*.json"))
        assert not list((root / ".staging").iterdir())
    finally:
        tree.close()


def test_staged_mutation_is_detected_before_rename(tmp_path: Path) -> None:
    def mutate(_kind: str, staged: Path, _final: Path) -> None:
        staged.write_bytes(b"mutated")

    tree = coverage._OutputTree(
        tmp_path / ".coverage",
        coverage.PublicationHooks(before_publish=mutate),
    )
    try:
        with pytest.raises(coverage.CoverageNormalizationError, match="staged bytes changed"):
            tree.publish_json({"stable": True}, directory=".summary", kind="summary")
    finally:
        tree.close()


def test_destination_mutation_is_detected_as_no_clobber_conflict(tmp_path: Path) -> None:
    def mutate(_kind: str, _staged: Path, final: Path) -> None:
        final.write_bytes(b"foreign")

    tree = coverage._OutputTree(
        tmp_path / ".coverage",
        coverage.PublicationHooks(before_publish=mutate),
    )
    try:
        with pytest.raises(coverage.CoverageNormalizationError, match="published object bytes changed"):
            tree.publish_json({"stable": True}, directory=".summary", kind="summary")
    finally:
        tree.close()


def test_atomic_no_clobber_has_one_winner_and_authenticates_replay(tmp_path: Path) -> None:
    parent = tmp_path / "race"
    parent.mkdir()
    first = parent / "first.tmp"
    second = parent / "second.tmp"
    target = parent / "target"
    first.write_bytes(b"same")
    second.write_bytes(b"same")
    results: list[bool] = []
    gate = threading.Barrier(2)

    def publish(path: Path) -> None:
        gate.wait()
        results.append(coverage._rename_noreplace(path, target))

    threads = [threading.Thread(target=publish, args=(path,)) for path in (first, second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == [False, True]
    loser = first if first.exists() else second
    assert hashlib.sha256(loser.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest()


def test_byte_identical_content_addressed_replay(tmp_path: Path) -> None:
    root = tmp_path / ".coverage"
    first = coverage._OutputTree(root, coverage.PublicationHooks())
    try:
        original = first.publish_json({"stable": [1, 2, 3]}, directory=".summary/0GUSDT", kind="summary")
    finally:
        first.close()
    second = coverage._OutputTree(root, coverage.PublicationHooks())
    try:
        replay = second.publish_json({"stable": [1, 2, 3]}, directory=".summary/0GUSDT", kind="summary")
        second.audit()
    finally:
        second.close()
    assert original.sha256 == replay.sha256
    assert replay.reused is True


def test_foreign_or_incomplete_output_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / ".coverage"
    tree = coverage._OutputTree(root, coverage.PublicationHooks())
    try:
        body = b"{}\n"
        foreign = root / ".daily" / f"{hashlib.sha256(body).hexdigest()}.json"
        foreign.parent.mkdir()
        foreign.write_bytes(body)
        with pytest.raises(coverage.CoverageNormalizationError, match="foreign, stale, or incomplete"):
            tree.audit()
    finally:
        tree.close()


def test_completion_byte_accounting_reaches_an_exact_fixed_point() -> None:
    document = {"metadata_ledger": {"measured_category_bytes": {"completion": 0}, "measured_metadata_bytes": 0}}
    body = coverage._completion_body(document, 123)
    decoded = json.loads(body)
    assert decoded["metadata_ledger"]["measured_category_bytes"]["completion"] == len(body)
    assert decoded["metadata_ledger"]["measured_metadata_bytes"] == 123 + len(body)
    assert decoded["metadata_ledger"]["measured_coverage_reservation_remaining_bytes"] == coverage.METADATA_BUDGET_BYTES - 123 - len(body)


def _fixture_row(schema: pa.Schema, **overrides: Any) -> dict[str, Any]:
    """Make a physical row from the real frozen Arrow schema, independently of the producer map."""
    row: dict[str, Any] = {}
    for field in schema:
        if field.name in overrides:
            row[field.name] = overrides[field.name]
        elif field.nullable:
            row[field.name] = None
        elif pa.types.is_dictionary(field.type) or pa.types.is_string(field.type):
            row[field.name] = "fixture"
        elif pa.types.is_integer(field.type):
            row[field.name] = 0
        elif pa.types.is_decimal(field.type):
            row[field.name] = Decimal("0")
        elif pa.types.is_boolean(field.type):
            row[field.name] = False
        elif pa.types.is_list(field.type):
            row[field.name] = []
        else:  # pragma: no cover - a new frozen type must be handled deliberately
            raise AssertionError(f"unsupported fixture type: {field.name} {field.type}")
    return row


def _write_json_document(path: Path, document: Mapping[str, Any]) -> tuple[str, int]:
    body = coverage._canonical_json(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return hashlib.sha256(body).hexdigest(), len(body)


def _write_real_partition(
    root: Path,
    product: str,
    symbol: str,
    month: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    schema = final_product_schema(product)
    parquet = root / "data" / f"{symbol}-{month}.parquet"
    parquet.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), parquet)
    parquet_body = parquet.read_bytes()
    parquet_sha = hashlib.sha256(parquet_body).hexdigest()
    lineage_document = {
        "required_product": product,
        "native_symbol": symbol,
        "utc_month": month,
        "row_count": len(rows),
        "parquet_sha256": parquet_sha,
    }
    lineage = root / "lineage" / f"{symbol}-{month}.json"
    lineage_sha, lineage_bytes = _write_json_document(lineage, lineage_document)
    return {
        "native_symbol": symbol,
        "utc_month": month,
        "row_count": len(rows),
        "parquet_path": str(parquet.relative_to(root)),
        "parquet_sha256": parquet_sha,
        "parquet_bytes": len(parquet_body),
        "lineage_path": str(lineage.relative_to(root)),
        "lineage_sha256": lineage_sha,
        "lineage_bytes": lineage_bytes,
    }


def _complete_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    allocation_overrides: Mapping[str, int] | None = None,
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    """Real report parsing and frozen schemas with bounded fixture-only pins."""
    accepted = [
        {**_member(), "accepted": True, "membership_class": "confirmed_perpetual",
         "in_archive": True, "in_current_exchange": True},
        {
            "symbol": "FUNDINGONLYUSDT",
            "accepted": True, "membership_class": "confirmed_perpetual",
            "in_archive": True, "in_current_exchange": False,
            "evidence": [{"kind": sizing.FUNDING_ONLY_EVIDENCE_CLASS,
                          "semantics": sizing.FUNDING_ONLY_SEMANTICS,
                          "families": ["monthly/fundingRate"],
                          "example_key": "data/futures/um/monthly/fundingRate/FUNDINGONLYUSDT/fixture.zip"}],
        },
        {"symbol": "ROWLESSUSDT", "accepted": True,
         "membership_class": "confirmed_perpetual", "in_archive": True,
         "in_current_exchange": False,
         "evidence": [{"onboard_ms": None, "closed_observed_ms": None}]},
    ]
    for row in (accepted[0], accepted[2]):
        row["evidence"][0].update(
            {"kind": "binance_exchange_info", "endpoint": "/fapi/v1/exchangeInfo",
             "contract_type": "PERPETUAL", "base_asset": row["symbol"][:-4],
             "quote_asset": "USDT", "margin_asset": "USDT"}
        )
    rejected = [{"symbol": "REJECTEDUSDT", "accepted": False,
                 "membership_class": "not_perpetual", "reason": "dated_future"}]
    report_document = {
        "membership": {"classifications": accepted + rejected},
        "product_matrix": [
            {"product": PRODUCT_BAR_1H, "universe_coverage_gaps": [
                {"symbol": "0GUSDT", "family_group": "klines",
                 "families": ["monthly-klines"], "kind": "head_gap_family_launch",
                 "status": "accepted_qualification_context", "blocking": False,
                 "observed_months": 1, "first_observed": "2025-09",
                 "last_observed": "2025-09", "family_first_observed": "2025-09",
                 "family_last_observed": "2025-09", "onboard_period": "2025-09",
                 "close_period": "", "missing_months": [], "missing_month_count": 0,
                 "objects": 1, "explained_by": "fixture_family_launch"}]},
            {"product": PRODUCT_MARK_INDEX_BASIS_1H,
             "typed_gap_symbols": ["FUNDINGONLYUSDT"]},
        ],
    }
    parser_counts = {
        "ACCEPTED_MEMBERSHIP_CLASSIFICATIONS": 4,
        "ACCEPTED_MEMBERSHIP_IDENTITIES": 3,
        "ACCEPTED_REJECTED_MEMBERSHIP_ROWS": 1,
        "ACCEPTED_SOURCE_COVERAGE_GAPS": 1,
        "ACCEPTED_TYPED_GAP_MEMBERSHIPS": 1,
        "ACCEPTED_FEE_AUTHORITY_GAPS": 3,
        "ACCEPTED_KNOWN_COVERAGE_ROWS": 4,
    }
    for name, value in parser_counts.items():
        monkeypatch.setattr(sizing, name, value)
    authority = coverage.prove_coverage_authority(report_document)

    input_parent = tmp_path / "accepted"
    product_roots = {name: input_parent / name for name in coverage.COMPLETION_SHA256}
    for root in product_roots.values():
        (root / ".complete").mkdir(parents=True)

    membership_rows = []
    for member in accepted:
        symbol = member["symbol"]
        membership_rows.append(
            _write_real_partition(
                product_roots["binance_usdm_perpetual_membership"],
                "binance_usdm_perpetual_membership", symbol, "authority",
                [_fixture_row(
                    final_product_schema("binance_usdm_perpetual_membership"),
                    **{**coverage.native_identity(symbol), **sizing.contract_evidence(member)},
                )],
            )
        )

    # Literal accepted fields keep the fixture independent of the producer map.
    bar_times = [_ms(17, hour) for hour in range(15, 24)] + _timestamps(range(18, 31), 24, 60)
    basis_times = [_ms(22, hour) for hour in range(10, 24)] + _timestamps(range(23, 31), 24, 60)
    oi_times = [_ms(17) + offset * 300_000 + 1_234 for offset in range(189, 288)]
    oi_times += [value + 1_234 for value in _timestamps(range(18, 31), 288, 5)]
    funding_times = [_ms(17, 8), _ms(17, 16)]
    funding_times += [_ms(day) + offset * 4 * 3_600_000 for day in range(18, 22) for offset in range(6)]
    funding_times += [_ms(22) + offset * 3_600_000 for offset in range(15)]
    funding_times += _timestamps(range(23, 31), 24, 60)
    observed = {
        PRODUCT_BAR_1H: ("open_time", bar_times),
        PRODUCT_TRADE_FLOW_1H: ("open_time", bar_times),
        PRODUCT_OPEN_INTEREST_5M: ("create_time", oi_times),
        PRODUCT_FUNDING_REALIZED: ("calc_time", funding_times),
        PRODUCT_FUNDING_INDICATIVE_1H: ("open_time", basis_times),
        PRODUCT_MARK_INDEX_BASIS_1H: ("open_time", basis_times),
        PRODUCT_LIQUIDATION_OBSERVED_DAILY: ("event_time_ms", [_ms(day, 12) for day in range(17, 31)]),
    }
    product_parts: dict[str, list[dict[str, Any]]] = {}
    for product, (field, timestamps) in observed.items():
        schema = final_product_schema(product)
        overrides: dict[str, Any] = {}
        if product == PRODUCT_LIQUIDATION_OBSERVED_DAILY:
            overrides = {"source_interval_seconds": 86_400,
                         "observation_semantics": "observed_and_censored",
                         "event_complete": False}
        rows = [
            _fixture_row(
                schema, **coverage.native_identity("0GUSDT"), **{field: value},
                **({"funding_interval_hours": 4 if value < _ms(22) else 1,
                    "last_funding_rate": Decimal("0.0001"),
                    "long_cashflow_rate": Decimal("-0.0001"),
                    "short_cashflow_rate": Decimal("0.0001")}
                   if product == PRODUCT_FUNDING_REALIZED else overrides),
            )
            for value in timestamps
        ]
        part = _write_real_partition(product_roots[product], product, "0GUSDT", "2025-09", rows)
        # Price-state descriptors resolve against their shared parent.
        if product in {PRODUCT_FUNDING_INDICATIVE_1H, PRODUCT_MARK_INDEX_BASIS_1H}:
            for key in ("parquet_path", "lineage_path"):
                part[key] = str(Path(product) / part[key])
        product_parts[product] = [part]
    product_parts[PRODUCT_FUNDING_REALIZED].append(
        _write_real_partition(
            product_roots[PRODUCT_FUNDING_REALIZED], PRODUCT_FUNDING_REALIZED,
            "FUNDINGONLYUSDT", "2025-09",
            [_fixture_row(final_product_schema(PRODUCT_FUNDING_REALIZED),
                          **coverage.native_identity("FUNDINGONLYUSDT"), calc_time=_ms(23))],
        )
    )

    quality_descriptors: dict[str, dict[str, Any]] = {}
    for product, start, end, count, kind in (
        (PRODUCT_OPEN_INTEREST_5M, _ms(17) + 1_234, _ms(17) + 1_234, 1, "missing_grid_run"),
        (PRODUCT_FUNDING_INDICATIVE_1H, None, None, 0, "unjoinable_source_range"),
        (PRODUCT_MARK_INDEX_BASIS_1H, _ms(22), _ms(22, 9), 10, "unjoinable_source_range"),
        (PRODUCT_LIQUIDATION_OBSERVED_DAILY, _ms(16), _ms(16), 1, "missing_daily_slot"),
    ):
        row = {**coverage.native_identity("0GUSDT"), "required_product": product,
               "utc_month": "2025-09", "missing_run_start_ms": start,
               "missing_run_end_ms": end, "expected_grid_count": count,
               "gap_kind": kind, "reason": "accepted_source_gap;availability_unknown"}
        root = product_roots[product]
        parquet_path = root / "quality" / "gaps.parquet"
        parquet_path.parent.mkdir()
        pq.write_table(pa.Table.from_pylist([row], schema=coverage.QUALITY_GAP_SCHEMA), parquet_path)
        body = parquet_path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        lineage_path = root / "quality" / "lineage.json"
        binding_field = "parquet_sha256" if product == PRODUCT_LIQUIDATION_OBSERVED_DAILY else "quality_gap_parquet_sha256"
        lineage_sha, lineage_bytes = _write_json_document(
            lineage_path, {"row_count": 1, binding_field: digest}
        )
        descriptor_root = root.parent if product in {PRODUCT_FUNDING_INDICATIVE_1H, PRODUCT_MARK_INDEX_BASIS_1H} else root
        quality_descriptors[product] = {
            "parquet_path": str(parquet_path.relative_to(descriptor_root)),
            "parquet_sha256": digest, "parquet_bytes": len(body),
            "lineage_path": str(lineage_path.relative_to(descriptor_root)),
            "lineage_sha256": lineage_sha, "lineage_bytes": lineage_bytes,
            "row_count": 1, "kind": kind,
        }

    cost_root = product_roots["binance_usdm_cost_calibration"]
    frozen_gap = cost_root / "authority" / "source-gaps.json"
    frozen_sha, frozen_bytes = _write_json_document(frozen_gap, {"row_count": 1})
    cost_parts: list[dict[str, Any]] = []
    for component, symbol, rows, source_days in (
        ("retained_book_depth", "0GUSDT", 7, ["2025-09-23"]),
        ("fee_authority_gap", "0GUSDT", 1, []),
        ("fee_authority_gap", "FUNDINGONLYUSDT", 1, []),
        ("fee_authority_gap", "ROWLESSUSDT", 1, []),
    ):
        parquet_path = cost_root / "data" / f"{component}-{symbol}.parquet"
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        component_schema = pa.schema([column.field() for column in cost_component_columns(component)])
        pq.write_table(
            pa.Table.from_pylist(
                [
                    _fixture_row(
                        component_schema,
                        **coverage.native_identity(symbol),
                    )
                    for _ in range(rows)
                ],
                schema=component_schema,
            ),
            parquet_path,
        )
        parquet_body = parquet_path.read_bytes()
        parquet_sha = hashlib.sha256(parquet_body).hexdigest()
        lineage_doc = {
            "component": component,
            "native_symbol": symbol,
            "row_count": rows,
            "parquet_sha256": parquet_sha,
            "raw_objects": [{"economic_day": day} for day in source_days],
        }
        lineage_path = cost_root / "lineage" / f"{component}-{symbol}.json"
        lineage_sha, lineage_bytes = _write_json_document(lineage_path, lineage_doc)
        cost_parts.append(
            {
                "component": component,
                "native_symbol": symbol,
                "utc_month": "authority" if not source_days else "2025-09",
                "row_count": rows,
                "parquet_path": str(parquet_path.relative_to(cost_root)),
                "parquet_sha256": parquet_sha,
                "parquet_bytes": len(parquet_body),
                "lineage_path": str(lineage_path.relative_to(cost_root)),
                "lineage_sha256": lineage_sha,
                "lineage_bytes": lineage_bytes,
            }
        )

    row_equations: dict[str, Mapping[str, Any]] = {
        PRODUCT_BAR_1H: {"physical_rows": 0, "product_rows": 0, "excluded_rows": 0, "collapsed_rows": 0, "duplicate_rows": 0, "overlap_rows": 0},
        PRODUCT_TRADE_FLOW_1H: {"physical_rows": 0, "product_rows": 0, "excluded_rows": 0, "collapsed_rows": 0, "duplicate_rows": 0, "overlap_rows": 0},
        PRODUCT_FUNDING_REALIZED: {"physical_source_rows": 0, "product_rows": 0, "excluded_source_rows": 0, "collapsed_identical_rows": 0, "inferred_events": 0, "conflicting_events": 0},
        PRODUCT_FUNDING_INDICATIVE_1H: {"physical_source_rows": 0, "joined_input_rows": 0, "unjoinable_source_rows": 0, "excluded_source_rows": 0, "collapsed_identical_rows": 0, "product_rows": 0, "fabricated_rows": 0},
        PRODUCT_MARK_INDEX_BASIS_1H: {"physical_source_rows": 0, "joined_input_rows": 0, "unjoinable_source_rows": 0, "excluded_source_rows": 0, "collapsed_identical_rows": 0, "product_rows": 0, "fabricated_rows": 0},
        PRODUCT_LIQUIDATION_OBSERVED_DAILY: {"inclusive_requested_slots": 0, "product_rows": 0, "missing_daily_slots": 0, "physical_source_rows": 0, "excluded_source_rows": 0, "collapsed_identical_rows": 0, "imputed_rows": 0},
    }
    completions: dict[str, dict[str, Any]] = {}
    for product in coverage.TIMESTAMP_COLUMNS:
        completion: dict[str, Any] = {
            "required_product": product,
            "schema_sha256": coverage.product_schema_identity(product),
            "schema": coverage._schema_contract(final_product_schema(product)),
            "partitions": product_parts[product],
        }
        if product == PRODUCT_OPEN_INTEREST_5M:
            completion["totals"] = {"physical_source_rows": len(oi_times), "product_rows": len(oi_times), "excluded_source_rows": 0, "collapsed_identical_source_rows": 0}
        else:
            equation = dict(row_equations[product])
            count = sum(part["row_count"] for part in product_parts[product])
            equation["product_rows"] = count
            if product in {PRODUCT_BAR_1H, PRODUCT_TRADE_FLOW_1H}:
                equation["physical_rows"] = count
            elif product in {PRODUCT_FUNDING_INDICATIVE_1H, PRODUCT_MARK_INDEX_BASIS_1H}:
                contributions = 1 if product == PRODUCT_FUNDING_INDICATIVE_1H else 3
                equation["joined_input_rows"] = count * contributions
                equation["unjoinable_source_rows"] = 1 if contributions == 1 else 30
                equation["physical_source_rows"] = count * contributions + equation["unjoinable_source_rows"]
            else:
                equation["physical_source_rows"] = count
            if product == PRODUCT_LIQUIDATION_OBSERVED_DAILY:
                equation["inclusive_requested_slots"] = count + 1
                equation["missing_daily_slots"] = 1
            completion["row_equation"] = equation
        if product == PRODUCT_LIQUIDATION_OBSERVED_DAILY:
            completion["gaps"] = [quality_descriptors[product]]
        elif product == PRODUCT_MARK_INDEX_BASIS_1H:
            completion["quality_gap_artifacts"] = [quality_descriptors[product]]
        elif product in quality_descriptors:
            completion["quality_gap_artifact"] = quality_descriptors[product]
        completions[product] = completion
    completions["binance_usdm_perpetual_membership"] = {
        "required_product": "binance_usdm_perpetual_membership",
        "schema_sha256": coverage.product_schema_identity("binance_usdm_perpetual_membership"),
        "schema": coverage._schema_contract(final_product_schema("binance_usdm_perpetual_membership")),
        "partitions": membership_rows,
        "membership_rows": 3,
        "detailed_metadata_rows": 2,
        "funding_only_rows": 1,
        "excluded_classifications": 1,
        "row_equation": {"classifications": 4, "accepted_membership_rows": 3, "excluded_classifications": 1},
    }
    completions["binance_usdm_cost_calibration"] = {
        "required_product": "binance_usdm_cost_calibration",
        "partitions": cost_parts,
        "frozen_source_gaps": {"row_count": 1, "path": str(frozen_gap.relative_to(cost_root)), "sha256": frozen_sha, "bytes": frozen_bytes},
        "source_equation": {"objects": 1, "generation0_objects": 1, "recovery_objects": 0, "physical_rows": 7, "retained_rows": 7, "deduplicated_rows": 0, "dropped_rows": 0},
        "fee_authority": {"gap_rows": 3, "official_historical_rows": 0, "missing_fee_is_zero": False},
        "scenario_policy": {"rows": 2, "historical_observation": False},
    }

    completion_pins: dict[str, str] = {}
    for product, document in completions.items():
        body = coverage._canonical_json(document)
        digest = hashlib.sha256(body).hexdigest()
        (product_roots[product] / ".complete" / f"{digest}.json").write_bytes(body)
        completion_pins[product] = digest

    report_path = tmp_path / "report.json"
    sizing_path = tmp_path / "sizing.json"
    holdout_path = tmp_path / "holdout.json"
    report_sha, _ = _write_json_document(report_path, report_document)
    bounds = {
        "SOURCE_GAP_BYTES": 1_000_000, "SOURCE_GAP_LARGEST_FILE": 1_000_000,
        "TYPED_GAP_BYTES": 1_000_000, "TYPED_GAP_LARGEST_FILE": 1_000_000,
        "QUALITY_GAP_ROWS": 100, "QUALITY_GAP_PARTITIONS": 20,
        "QUALITY_GAP_BYTES": 1_000_000, "QUALITY_GAP_LARGEST_FILE": 1_000_000,
        "METADATA_PAGE_BYTES": 100_000,
    }
    bounds.update(allocation_overrides or {})
    metadata_bytes = 22 * bounds["METADATA_PAGE_BYTES"]
    sizing_document = {
        "coverage_authority": {
            "accepted_source_coverage_gaps": 1,
            "source_gap_component": {"schema": coverage._schema_contract(coverage.SOURCE_GAP_SCHEMA), "projected_rows": 1, "partition_count": 1, "projected_bytes": bounds["SOURCE_GAP_BYTES"], "largest_partition_bytes": bounds["SOURCE_GAP_LARGEST_FILE"]},
            "typed_gap_membership_component": {"schema": coverage._schema_contract(coverage.TYPED_GAP_SCHEMA), "projected_rows": 1, "partition_count": 1, "projected_bytes": bounds["TYPED_GAP_BYTES"], "largest_partition_bytes": bounds["TYPED_GAP_LARGEST_FILE"]},
            "quality_gap_component": {"schema": coverage._schema_contract(coverage.QUALITY_GAP_SCHEMA), "projected_rows": bounds["QUALITY_GAP_ROWS"], "partition_count": bounds["QUALITY_GAP_PARTITIONS"], "projected_bytes": bounds["QUALITY_GAP_BYTES"], "largest_partition_bytes": bounds["QUALITY_GAP_LARGEST_FILE"]},
        },
        "capacity": {"catalog_manifest_bundle_bytes": metadata_bytes + 1_000_000},
        "partitioning": {"catalog_page_bytes": bounds["METADATA_PAGE_BYTES"]},
    }
    sizing_sha, _ = _write_json_document(sizing_path, sizing_document)
    holdout_sha, _ = _write_json_document(holdout_path, {"boundary_id": "fixture-boundary", "boundary_utc": "2025-09-30T00:00:00+00:00"})
    pins = {
        "REPORT_SHA256": report_sha, "SIZING_SHA256": sizing_sha,
        "HOLDOUT_SHA256": holdout_sha, "HOLDOUT_ID": "fixture-boundary",
        "HOLDOUT_UTC": "2025-09-30T00:00:00+00:00", "COMPLETION_SHA256": completion_pins,
        "ACCEPTED_MEMBERSHIP_IDENTITIES": 3, "DETAILED_MEMBERSHIP_IDENTITIES": 2,
        "FUNDING_ONLY_MEMBERSHIP_IDENTITIES": 1, "ACCEPTED_REJECTED_MEMBERSHIP_ROWS": 1,
        "ACCEPTED_SOURCE_COVERAGE_GAPS": 1, "ACCEPTED_TYPED_GAP_MEMBERSHIPS": 1,
        "SOURCE_GAP_ROWS": 1, "SOURCE_GAP_PARTITIONS": 1,
        "TYPED_GAP_ROWS": 1, "TYPED_GAP_PARTITIONS": 1,
        "METADATA_PAGE_COUNTS": {"source_gap": 1, "typed_gap": 1, "quality_gap": 20},
        "METADATA_BUDGET_BYTES": metadata_bytes,
        "RELEASE_METADATA_BYTES": metadata_bytes + 1_000_000,
        "RELEASE_METADATA_REMAINDER_BYTES": 1_000_000, "COST_SOURCE_GAP_ROWS": 1,
        **bounds,
    }
    for name, value in pins.items():
        monkeypatch.setattr(coverage, name, value)
    return {
        "report_path": report_path, "sizing_path": sizing_path, "holdout_path": holdout_path,
        "product_roots": product_roots, "output_root": tmp_path / ".coverage",
    }, authority


def _published_manifest(root: Path, completion: Mapping[str, Any], name: str) -> dict[str, Any]:
    descriptor = completion["manifests"][name]
    path = root / descriptor["path"]
    body = path.read_bytes()
    assert hashlib.sha256(body).hexdigest() == descriptor["sha256"]
    assert len(body) == descriptor["bytes"]
    return json.loads(body)


def _assert_no_completion(root: Path) -> None:
    assert not list((root / ".complete").glob("*.json"))


def _output_facts(root: Path) -> dict[str, tuple[str, int, int]]:
    return {
        str(path.relative_to(root)): (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            path.stat().st_ino,
            path.stat().st_mtime_ns,
        )
        for path in root.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize("relative_first", [False, True])
def test_complete_producer_authenticates_real_shapes_and_replays_byte_identically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative_first: bool
) -> None:
    arguments, authority = _complete_fixture(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    root = arguments["output_root"]
    arguments["output_root"] = Path(".coverage") if relative_first else root
    report, _sizing, _holdout, products = coverage.load_inputs(
        report_path=arguments["report_path"],
        sizing_path=arguments["sizing_path"],
        holdout_path=arguments["holdout_path"],
        product_roots=arguments["product_roots"],
    )
    assert coverage.prove_coverage_authority is sizing.prove_coverage_authority
    assert coverage.prove_coverage_authority(report) == authority
    assert products[PRODUCT_OPEN_INTEREST_5M].schema.names.count("create_time") == 1
    assert len(authority["membership"]["accepted"]) == 3
    assert len(authority["membership"]["rejected"]) == 1
    for product in (PRODUCT_FUNDING_INDICATIVE_1H, PRODUCT_MARK_INDEX_BASIS_1H):
        assert products[product].descriptor_root == products[product].root.parent
        descriptor = products[product].completion["partitions"][0]
        assert Path(descriptor["parquet_path"]).parts[0] == product
    for member in authority["membership"]["accepted"]:
        evidence = sizing.contract_evidence(member)
        assert evidence["contract_type"] == "PERPETUAL"
        if member["symbol"] == "FUNDINGONLYUSDT":
            assert evidence["onboard_ms"] is None
            assert evidence["base_asset"] is None

    first = coverage.normalize_coverage(**arguments)
    completion_body = first.completion_path.read_bytes()
    completion = json.loads(completion_body)
    assert first.completion_reused is False
    assert (first.source_gap_rows, first.typed_gap_rows, first.quality_gap_rows) == (1, 1, 4)
    assert completion["membership"] == {
        "accepted_identities": 3, "excluded_classifications": 1,
        "funding_only_identities": 1, "product_absence_removes_membership": False,
    }
    alignment = completion["alignment"]
    assert alignment["daily_report_equation"]["published_partitions"] == 3
    assert alignment["aligned_day_rows"] == 90
    assert alignment["five_product_observed_day_count"] == 9
    assert alignment["full_cadence_day_count"] == 8
    assert completion["components"]["source_gap"]["parquet_bytes"] <= 1_000_000
    assert completion["components"]["typed_gap_membership"]["largest_file_bytes"] <= 1_000_000
    assert completion["metadata_ledger"]["measured_metadata_bytes"] <= coverage.METADATA_BUDGET_BYTES
    daily_manifest = _published_manifest(root, completion, "daily")
    daily_ref = next(row for row in daily_manifest["rows"] if row["native_symbol"] == "0GUSDT")
    daily = _read_published_json(root, ".daily/0GUSDT/2025-09", daily_ref["sha256"])
    days = {row[0]: row for row in daily["days"]}
    assert days["2025-09-22"][1][3] == 14
    assert days["2025-09-22"][5:] == [True, False]
    assert days["2025-09-23"][5:] == [True, True]
    assert all(days[f"2025-09-{day:02d}"][5:] == [True, True] for day in range(23, 31))
    summaries = _published_manifest(root, completion, "summary")
    by_symbol = {
        ref["native_symbol"]: _read_published_json(
            root, f".summary/{ref['native_symbol']}", ref["sha256"]
        )
        for ref in summaries["rows"]
    }
    rowless = by_symbol["ROWLESSUSDT"]
    assert all(row["observed_count"] == 0 for row in rowless["products"]
               if row["required_product"] != "binance_usdm_cost_calibration")
    funding_only = {row["required_product"]: row for row in by_symbol["FUNDINGONLYUSDT"]["products"]}
    assert funding_only[PRODUCT_FUNDING_REALIZED]["observed_count"] == 1
    assert funding_only[PRODUCT_FUNDING_REALIZED]["expected_count"] is None
    assert funding_only[PRODUCT_BAR_1H]["observed_count"] == 0
    main = {row["required_product"]: row for row in by_symbol["0GUSDT"]["products"]}
    assert main[PRODUCT_BAR_1H]["observed_count"] == 321
    assert main[PRODUCT_BAR_1H]["qualification_source_gap_context"][0]["gap_kind"] == "head_gap_family_launch"
    assert main[PRODUCT_BAR_1H]["quality_gap_partitions"] == []
    assert main[PRODUCT_OPEN_INTEREST_5M]["missing_count"] == 1
    assert main[PRODUCT_OPEN_INTEREST_5M]["observed_count"] == 3_843
    assert main[PRODUCT_MARK_INDEX_BASIS_1H]["missing_count"] == 10
    assert main[PRODUCT_LIQUIDATION_OBSERVED_DAILY]["missing_count"] == 1
    cost_summary = main["binance_usdm_cost_calibration"]
    assert cost_summary["observed_count"] is None
    assert cost_summary["component_counts"] == [
        {"component": "fee_authority_gap", "row_count": 1, "unit": "authority_gap_rows"},
        {"component": "retained_book_depth", "row_count": 7, "unit": "normalized_book_depth_rows"},
    ]
    assert cost_summary["source_day_extrema"] == [
        {"component": "retained_book_depth", "first_source_day": "2025-09-23", "last_source_day": "2025-09-23"}
    ]
    quality = _published_manifest(root, completion, "quality_gap")
    assert quality["row_count"] == 4
    assert {row["required_product"] for row in quality["rows"]} == {
        PRODUCT_OPEN_INTEREST_5M, PRODUCT_FUNDING_INDICATIVE_1H,
        PRODUCT_MARK_INDEX_BASIS_1H, PRODUCT_LIQUIDATION_OBSERVED_DAILY,
    }
    source_manifest = _published_manifest(root, completion, "source_gap")
    source_ref = source_manifest["rows"][0]
    source_path = root / ".source-gaps" / PRODUCT_BAR_1H / "0GUSDT" / "authority" / f"{source_ref['parquet_sha256']}.parquet"
    assert pq.ParquetFile(source_path).read().to_pylist()[0] == {
        **coverage.native_identity("0GUSDT"), **authority["source_gaps"][0],
    }
    excluded = _published_manifest(root, completion, "excluded_membership")
    assert excluded["rows"] == list(authority["membership"]["rejected"])
    assert set(by_symbol) == {"0GUSDT", "FUNDINGONLYUSDT", "ROWLESSUSDT"}
    facts = _output_facts(root)
    arguments["output_root"] = root if relative_first else Path(".coverage")
    second = coverage.normalize_coverage(**arguments)
    assert second.completion_reused is True
    assert second.completion_sha256 == first.completion_sha256
    assert second.completion_path.read_bytes() == completion_body
    assert _output_facts(root) == facts
    assert list((root / ".staging").iterdir()) == []


@pytest.mark.parametrize("entry", ["digest_file", "directory", "fifo", "symlink"])
def test_complete_producer_refuses_foreign_inventory_before_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    arguments, _authority = _complete_fixture(tmp_path, monkeypatch)
    root = arguments["output_root"]
    root.mkdir()
    if entry == "digest_file":
        body = b"{}\n"
        foreign = root / f"{hashlib.sha256(body).hexdigest()}.json"
        foreign.write_bytes(body)
        match = "foreign, stale, or incomplete"
    elif entry == "directory":
        foreign = root / "unexpected"
        foreign.mkdir()
        match = "unexpected directory"
    elif entry == "fifo":
        foreign = root / "unexpected_fifo"
        os.mkfifo(foreign)
        match = "non-regular"
    else:
        foreign = root / "unexpected_link"
        foreign.symlink_to(arguments["report_path"])
        match = "non-regular"
    with pytest.raises(coverage.CoverageNormalizationError, match=match):
        coverage.normalize_coverage(**arguments)
    _assert_no_completion(root)
    assert foreign.lstat()
    assert list((root / ".staging").iterdir()) == []


@pytest.mark.parametrize("boundary", ["source-gaps", "completion"])
def test_complete_producer_refuses_staged_replacement_without_deleting_foreign_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    arguments, _authority = _complete_fixture(tmp_path, monkeypatch)
    replaced: list[Path] = []

    def replace(kind: str, temporary: Path, _final: Path) -> None:
        if kind == boundary:
            replacement = tmp_path / "foreign-stage"
            replacement.write_bytes(temporary.read_bytes())
            os.replace(replacement, temporary)
            replaced.append(temporary)

    with pytest.raises(coverage.CoverageNormalizationError, match="held staged object was replaced"):
        coverage.normalize_coverage(**arguments, hooks=coverage.PublicationHooks(before_publish=replace))
    _assert_no_completion(arguments["output_root"])
    assert len(replaced) == 1
    assert list((arguments["output_root"] / ".staging").iterdir()) == replaced
    assert replaced[0].read_bytes()


@pytest.mark.parametrize("dependency", [
    "report", "sizing", "holdout", "completion", "membership_parquet",
    "membership_lineage", "timestamp_parquet", "timestamp_lineage",
    "quality_parquet", "quality_lineage", "cost_lineage", "cost_source_gap",
])
def test_complete_producer_reproves_consumed_inputs_after_completion_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dependency: str
) -> None:
    arguments, _authority = _complete_fixture(tmp_path, monkeypatch)
    roots = arguments["product_roots"]
    product = roots[PRODUCT_OPEN_INTEREST_5M]
    targets = {
        "report": arguments["report_path"], "sizing": arguments["sizing_path"],
        "holdout": arguments["holdout_path"],
        "completion": next((product / ".complete").glob("*.json")),
        "membership_parquet": roots["binance_usdm_perpetual_membership"] / "data/0GUSDT-authority.parquet",
        "membership_lineage": roots["binance_usdm_perpetual_membership"] / "lineage/0GUSDT-authority.json",
        "timestamp_parquet": product / "data/0GUSDT-2025-09.parquet",
        "timestamp_lineage": product / "lineage/0GUSDT-2025-09.json",
        "quality_parquet": product / "quality/gaps.parquet",
        "quality_lineage": product / "quality/lineage.json",
        "cost_lineage": roots["binance_usdm_cost_calibration"] / "lineage/retained_book_depth-0GUSDT.json",
        "cost_source_gap": roots["binance_usdm_cost_calibration"] / "authority/source-gaps.json",
    }
    target = targets[dependency]
    original = target.read_bytes()
    called = False

    def mutate(kind: str, _temporary: Path, final: Path) -> None:
        nonlocal called
        if kind == "completion":
            called = True
            assert not final.exists()
            target.write_bytes(original + b" ")

    with pytest.raises(coverage.CoverageNormalizationError, match="digest changed|artifact changed|lineage changed|changed before completion"):
        coverage.normalize_coverage(**arguments, hooks=coverage.PublicationHooks(before_publish=mutate))
    assert called
    _assert_no_completion(arguments["output_root"])
    assert target.read_bytes() == original + b" "
    assert list((arguments["output_root"] / ".staging").iterdir()) == []


def test_complete_producer_reproves_published_report_after_completion_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arguments, _authority = _complete_fixture(tmp_path, monkeypatch)
    changed: list[Path] = []

    def mutate(kind: str, _temporary: Path, final: Path) -> None:
        if kind == "completion":
            assert not final.exists()
            report = next((arguments["output_root"] / ".daily").rglob("*.json"))
            report.write_bytes(report.read_bytes() + b" ")
            changed.append(report)

    with pytest.raises(coverage.CoverageNormalizationError, match="published object bytes changed"):
        coverage.normalize_coverage(**arguments, hooks=coverage.PublicationHooks(before_publish=mutate))
    assert len(changed) == 1
    _assert_no_completion(arguments["output_root"])
    assert list((arguments["output_root"] / ".staging").iterdir()) == []


def test_complete_producer_interrupted_completion_resumes_without_rewriting_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arguments, _authority = _complete_fixture(tmp_path, monkeypatch)
    root = arguments["output_root"]
    prospective: list[bytes] = []

    def interrupt(kind: str, temporary: Path, final: Path) -> None:
        if kind == "completion":
            assert not final.exists()
            prospective.append(temporary.read_bytes())
            raise RuntimeError("fixture completion interruption")

    with pytest.raises(RuntimeError, match="fixture completion interruption"):
        coverage.normalize_coverage(**arguments, hooks=coverage.PublicationHooks(before_publish=interrupt))
    _assert_no_completion(root)
    assert len(prospective) == 1
    assert list((root / ".staging").iterdir()) == []
    facts = _output_facts(root)
    assert any(name.startswith(".daily/") for name in facts)
    resumed = coverage.normalize_coverage(**arguments)
    assert resumed.completion_reused is False
    assert resumed.completion_path.read_bytes() == prospective[0]
    assert {name: value for name, value in _output_facts(root).items() if not name.startswith(".complete/")} == facts
    completed = _output_facts(root)
    replay = coverage.normalize_coverage(**arguments)
    assert replay.completion_reused is True
    assert replay.completion_sha256 == resumed.completion_sha256
    assert _output_facts(root) == completed


@pytest.mark.parametrize("bound,match", [
    ("SOURCE_GAP_BYTES", "source-gap byte bound exceeded"),
    ("SOURCE_GAP_LARGEST_FILE", "source-gap byte bound exceeded"),
    ("TYPED_GAP_BYTES", "typed-gap byte bound exceeded"),
    ("TYPED_GAP_LARGEST_FILE", "typed-gap byte bound exceeded"),
    ("QUALITY_GAP_BYTES", "quality-gap byte bound exceeded"),
    ("QUALITY_GAP_LARGEST_FILE", "quality-gap byte bound exceeded"),
    ("QUALITY_GAP_ROWS", "quality-gap allocation count exceeded"),
    ("QUALITY_GAP_PARTITIONS", "quality-gap allocation count exceeded"),
    ("METADATA_PAGE_BYTES", "coverage metadata budget exceeded"),
])
def test_complete_producer_refuses_component_and_metadata_overrun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bound: str, match: str
) -> None:
    arguments, _authority = _complete_fixture(tmp_path, monkeypatch, allocation_overrides={bound: 1})
    with pytest.raises(coverage.CoverageNormalizationError, match=match):
        coverage.normalize_coverage(**arguments)
    _assert_no_completion(arguments["output_root"])
    assert list((arguments["output_root"] / ".staging").iterdir()) == []
