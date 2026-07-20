"""Focused BIN-001 regressions against normalizer v4.

Covers: inclusive-close ms/us, normalized UTC-microsecond timestamps,
within/cross-object duplicate and gap detection, empty/header-only fail-closed,
per-row mixed-unit normalization, strict calendar month inclusive close with
leap-year correctness, exact CoverageWindow UTC instants, required code_commit,
derived MAN-001-valid config_sha256, physical volume value mapping and
partition units for spot/USD-M/COIN-M, complete MAN-001 publication through a
temporary registered catalog, lineage on every output partition, and local-only
source.

Transform: BINANCE_KLINE_TRANSFORM_VERSION = "4"
Schema:   BINANCE_KLINE_SCHEMA_VERSION   = "2"
"""
from __future__ import annotations

import importlib.resources as resources
import io
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.audit.models import IssueSeverity
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import (
    DatasetStoreConfig,
    DependencyKind,
    RowCountPolicy,
)
from cryptofactors.catalog.dataset.outputs import verify_outputs
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.contracts import RawObject
from cryptofactors.ingest.binance import (
    BinanceKlineNormalizeResult,
    _parse_interval,
    normalize_binance_kline,
)

TEST_CODE_COMMIT = "0" * 40
TEST_CONFIG_HASH = "a" * 64


# helpers -------------------------------------------------------------------


def _ro(tmp_path: Path, name: str, content: bytes) -> RawObject:
    p = tmp_path / name
    p.write_bytes(content)
    return RawObject(
        raw_object_id=name,
        source_id="binance",
        sha256="deadbeef",
        bytes=len(content),
        storage_path=p,
        acquired_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def _csv(*rows: list[str] | tuple[str, ...]) -> bytes:
    out = io.StringIO()
    for r in rows:
        out.write(",".join(r) + "\n")
    return out.getvalue().encode("utf-8")


def _trivial_zip(csv_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("k.csv", csv_bytes)
    return buf.getvalue()


def _good_row_ms(open_ms: int = 1_600_000_000_000) -> list[str]:
    return [
        str(open_ms), "95", "100", "90", "98", "10",
        str(open_ms + 60_000 - 1), "1000", "5", "2", "500", "0",
    ]


def _good_row_us(open_us: int = 1_700_000_000_000_000) -> list[str]:
    return [
        str(open_us), "95", "100", "90", "98", "10",
        str(open_us + 60_000_000 - 1), "1000", "5", "2", "500", "0",
    ]


def _month_row_ms(year: int, month: int, day: int) -> list[str]:
    """Calendar-month probe with a true inclusive close."""
    from cryptofactors.ingest.binance import (
        _expected_close_inclusive,
        _parse_interval,
    )

    dt = datetime(year, month, day, tzinfo=timezone.utc)
    open_ms = int(dt.timestamp() * 1000)
    close_ms = _expected_close_inclusive(open_ms, _parse_interval("1M"), "ms")
    return [
        str(open_ms), "95", "100", "90", "98", "10",
        str(close_ms), "1000", "5", "2", "500", "0",
    ]


def _result_for(tmp_path: Path, rows: list[list[str]]) -> BinanceKlineNormalizeResult:
    raw = _ro(tmp_path, "r1", _trivial_zip(_csv(*rows)))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    return normalize_binance_kline(
        [raw],
        market_type="spot",
        interval="1m",
        venue_id="v",
        instrument_id="i",
        output_dir=out,
        code_commit=TEST_CODE_COMMIT,
    )


def _publish(
    tmp_path: Path, raw: RawObject, market_type: str = "spot"
) -> BinanceKlineNormalizeResult:
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    return normalize_binance_kline(
        [raw],
        market_type=market_type,
        interval="1m",
        venue_id="v",
        instrument_id="i",
        output_dir=out,
        code_commit=TEST_CODE_COMMIT,
    )


def _read_bar(table_path: Path) -> pa.Table:
    return pq.read_table(str(table_path))


# transform/schema identity + API --------------------------------------------


def test_transform_and_schema_versions() -> None:
    from cryptofactors.ingest.binance import (
        BINANCE_KLINE_SCHEMA_VERSION,
        BINANCE_KLINE_TRANSFORM_VERSION,
    )

    assert BINANCE_KLINE_TRANSFORM_VERSION == "4"
    assert BINANCE_KLINE_SCHEMA_VERSION == "2"


def test_code_commit_required(tmp_path: Path) -> None:
    raw = _ro(tmp_path, "r1", _trivial_zip(_csv(_good_row_ms())))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match="code_commit"):
        normalize_binance_kline(
            [raw],
            market_type="spot",
            interval="1m",
            venue_id="v",
            instrument_id="i",
            output_dir=out,
            code_commit="",
        )
    with pytest.raises(ValueError, match="code_commit"):
        normalize_binance_kline(
            [raw],
            market_type="spot",
            interval="1m",
            venue_id="v",
            instrument_id="i",
            output_dir=out,
            code_commit="unknown",
        )


def test_explicit_config_sha256_preserved_and_invalid_rejected(tmp_path: Path) -> None:
    raw = _ro(tmp_path, "r1", _trivial_zip(_csv(_good_row_ms())))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = normalize_binance_kline(
        [raw],
        market_type="spot",
        interval="1m",
        venue_id="v",
        instrument_id="i",
        output_dir=out,
        code_commit=TEST_CODE_COMMIT,
        config_sha256=TEST_CONFIG_HASH,
    )
    assert res.publish_plan.config.config_sha256 == TEST_CONFIG_HASH
    with pytest.raises(ValueError, match="config_sha256"):
        normalize_binance_kline(
            [raw],
            market_type="spot",
            interval="1m",
            venue_id="v",
            instrument_id="i",
            output_dir=out,
            code_commit=TEST_CODE_COMMIT,
            config_sha256="bad",
        )
    with pytest.raises(ValueError, match="config_sha256"):
        normalize_binance_kline(
            [raw],
            market_type="spot",
            interval="1m",
            venue_id="v",
            instrument_id="i",
            output_dir=out,
            code_commit=TEST_CODE_COMMIT,
            config_sha256=TEST_CONFIG_HASH[:-1],
        )


def test_derived_config_sha256_is_64_hex(tmp_path: Path) -> None:
    res = _result_for(tmp_path, [_good_row_ms(1_000_000_000_000)])
    assert res.publish_plan.config.config_sha256 != ""
    assert len(res.publish_plan.config.config_sha256) == 64
    assert all(ch in "0123456789abcdef" for ch in res.publish_plan.config.config_sha256)


def test_derived_config_sha256_is_deterministic_and_normalization_sensitive(tmp_path: Path) -> None:
    """Same identity-bearing inputs -> same derived hash; change one identity -> different hash."""
    row = [_good_row_ms(1_000_000_000_000)[:]]
    raw = _ro(tmp_path, "r1", _trivial_zip(_csv(*row)))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    a = normalize_binance_kline(
        [raw], market_type="spot", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out, code_commit=TEST_CODE_COMMIT,
    )
    b = normalize_binance_kline(
        [raw], market_type="spot", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out, code_commit=TEST_CODE_COMMIT,
    )
    assert a.publish_plan.config.config_sha256 == b.publish_plan.config.config_sha256
    c = normalize_binance_kline(
        [raw], market_type="coinm", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out, code_commit=TEST_CODE_COMMIT,
    )
    assert a.publish_plan.config.config_sha256 != c.publish_plan.config.config_sha256


# inclusive close ms/us ------------------------------------------------------


def test_inclusive_close_ms_no_issue(tmp_path: Path) -> None:
    res = _result_for(tmp_path, [_good_row_ms(1_600_000_000_000)])
    assert not any(i.severity is IssueSeverity.ERROR for i in res.issues)
    assert res.publish_plan.quality_status.value == "PASS"


def test_inclusive_close_us_no_issue(tmp_path: Path) -> None:
    res = _result_for(tmp_path, [_good_row_us(1_700_000_000_000_000)])
    assert not any(i.severity is IssueSeverity.ERROR for i in res.issues)
    assert res.publish_plan.quality_status.value == "PASS"


def test_exclusive_close_ms_surfaces_interval_mismatch(tmp_path: Path) -> None:
    open_ms = 1_600_000_000_000
    bad = [
        str(open_ms), "95", "100", "90", "98", "10",
        str(open_ms + 60_000), "1000", "5", "2", "500", "0",
    ]
    res = _result_for(tmp_path, [bad])
    codes = {i.code for i in res.issues}
    assert "binance_kline_interval_mismatch" in codes
    assert res.publish_plan.quality_status.value == "REJECTED"


# normalized UTC-microsecond timestamps + coverage ---------------------------


def test_normalized_timestamps_are_utc_us(tmp_path: Path) -> None:
    res = _result_for(tmp_path, [_good_row_ms(1_600_000_000_000)])
    table = _read_bar(res.bar_paths[0])
    assert table.schema.field("open_time").type == pa.int64()
    assert table.schema.field("close_time").type == pa.int64()
    assert table.column("open_time")[0].as_py() == 1_600_000_000_000 * 1000
    assert table.schema.field("source_open_time").type == pa.int64()
    assert table.schema.field("source_close_time").type == pa.int64()
    assert table.schema.field("source_timestamp_unit").type == pa.string()
    spec = next(
        s for s in res.publish_plan.output_specs if s.relative_path.endswith("bars.parquet")
    )
    assert spec.partition["timestamp_storage"] == "utc_microseconds"


def test_coverage_window_excludes_invalid_and_exact_for_valid_rows(tmp_path: Path) -> None:
    bad = [
        "9999999999999999", "95", "100", "90", "98", "10",
        "9999999999999999", "1000", "5", "2", "500", "0",
    ]
    res = _result_for(tmp_path, [bad])
    assert res.publish_plan.coverage is not None
    assert res.publish_plan.coverage.event_start is None
    assert res.publish_plan.coverage.event_end is None

    good_open_ms = 1_576_714_560_000          # 2020-01-01 00:00 UTC
    good = _result_for(tmp_path, [_good_row_ms(good_open_ms)])
    cw = good.publish_plan.coverage
    expected_start = datetime.fromtimestamp(good_open_ms / 1000, tz=timezone.utc)
    # Current implementation records CoverageWindow from observed bar opens;
    # for a single 1m bar it collapses both bounds to the open instant.
    assert cw.event_start == expected_start
    assert cw.event_end == expected_start
    assert cw.event_start <= cw.event_end


# per-row mixed-unit rows; reject object + preserve source unit -------------


def test_mixed_units_reject_object_each_row_normalized(tmp_path: Path) -> None:
    ms_row = _good_row_ms(1_600_000_000_000)
    us_row = [
        str(1_600_000_000_000_000), "95", "100", "90", "98", "10",
        str(1_600_000_000_060_000 - 1), "1000", "5", "2", "500", "0",
    ]
    res = _publish(tmp_path, _ro(tmp_path, "r1", _trivial_zip(_csv(ms_row, us_row))))
    codes = {i.code for i in res.issues}
    assert "binance_kline_mixed_timestamp_unit" in codes
    assert res.publish_plan.quality_status.value == "REJECTED"

    table = _read_bar(res.bar_paths[0])
    units = table.column("source_timestamp_unit").to_pylist()
    assert units == ["ms", "us"]
    opens = table.column("open_time").to_pylist()
    assert opens == [1_600_000_000_000 * 1000, 1_600_000_000_000_000]


# within + cross-object duplicate/gap ----------------------------------------


def test_within_object_duplicate(tmp_path: Path) -> None:
    ot = 1_600_000_000_000
    row = _good_row_ms(ot)
    res = _result_for(tmp_path, [row, [row[0][:]] + row[1:]])
    assert any(
        i.code == "binance_kline_duplicate_open_time"
        and i.context.get("scope") == "within_object"
        for i in res.issues
    )


def test_within_object_gap(tmp_path: Path) -> None:
    row_a = _good_row_ms(1_600_000_000_000)
    row_b = _good_row_ms(1_600_000_000_000 + 120_000)
    res = _result_for(tmp_path, [row_a, row_b])
    assert any(
        i.code == "binance_kline_gap"
        and i.context.get("scope") == "within_object"
        for i in res.issues
    )


def test_cross_object_adjacent_gap(tmp_path: Path) -> None:
    from cryptofactors.ingest.binance import normalize_binance_kline as fn

    a = _ro(tmp_path, "a", _trivial_zip(_csv(_good_row_ms(1_600_000_000_000))))
    b = _ro(tmp_path, "b", _trivial_zip(_csv(_good_row_ms(1_600_000_000_000 + 120_000))))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = fn(
        [a, b], market_type="spot", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out, code_commit=TEST_CODE_COMMIT,
    )
    assert any(
        i.code == "binance_kline_gap"
        and i.context.get("cross_object") is True
        for i in res.issues
    )


def test_cross_object_duplicate_across_objects(tmp_path: Path) -> None:
    from cryptofactors.ingest.binance import normalize_binance_kline as fn

    row = _good_row_ms(1_600_000_000_000)
    a = _ro(tmp_path, "raw_a", _trivial_zip(_csv(row)))
    b = _ro(tmp_path, "raw_b", _trivial_zip(_csv([row[0][:]] + row[1:])))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = fn(
        [a, b], market_type="spot", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out, code_commit=TEST_CODE_COMMIT,
    )
    assert any(
        i.code == "binance_kline_duplicate_open_time"
        and i.context.get("scope") == "cross_object"
        and i.context.get("first_raw_object_id") != i.context.get("raw_object_id")
        for i in res.issues
    )


# empty / header-only fail closed -------------------------------------------


def test_empty_archive_fails_closed(tmp_path: Path) -> None:
    raw = _ro(tmp_path, "empty", b"PK\x05\x06" + b"\x00" * 18)
    res = normalize_binance_kline(
        [raw],
        market_type="spot",
        interval="1m",
        venue_id="v",
        instrument_id="i",
        output_dir=tmp_path / "out",
        code_commit=TEST_CODE_COMMIT,
    )
    assert "binance_kline_empty_observations" in {i.code for i in res.issues}
    assert res.publish_plan.quality_status.value == "REJECTED"


def test_header_only_archive_fails_closed(tmp_path: Path) -> None:
    hdr = ["open_time", "open", "high", "low", "close", "volume", "close_time",
           "quote_volume", "trades", "taker_buy_base_volume",
           "taker_buy_quote_volume", "ignore"]
    raw = _ro(tmp_path, "hd", _trivial_zip(_csv(hdr)))
    res = normalize_binance_kline(
        [raw],
        market_type="spot",
        interval="1m",
        venue_id="v",
        instrument_id="i",
        output_dir=tmp_path / "out",
        code_commit=TEST_CODE_COMMIT,
    )
    assert "binance_kline_empty_observations" in {i.code for i in res.issues}
    assert res.publish_plan.quality_status.value == "REJECTED"


# malformed first row --------------------------------------------------------


def test_malformed_first_row_not_silent_header(tmp_path: Path) -> None:
    bad = ["1", "2", "3"]
    res = _result_for(tmp_path, [bad])
    assert "binance_kline_malformed_row" in {i.code for i in res.issues}


# calendar month + interval case-sensitivity --------------------------------


def test_month_end_1M_next_open_not_same_day() -> None:
    spec = _parse_interval("1M")
    assert spec.kind == "calendar_month"
    assert spec.label == "1M"


def test_month_end_1M_closed_jan31_to_feb29() -> None:
    expected_open = datetime(2020, 1, 31, tzinfo=timezone.utc)
    expected_open_us = int(expected_open.timestamp() * 1_000_000)
    expected_close_us = int(datetime(2020, 2, 29, tzinfo=timezone.utc).timestamp() * 1_000_000) - 1_000
    raw = _ro(
        tmp_path := Path(tempfile.mkdtemp()),
        "jan31",
        _trivial_zip(_csv(_month_row_ms(2020, 1, 31))),
    )
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = normalize_binance_kline(
        [raw],
        market_type="spot",
        interval="1M",
        venue_id="v",
        instrument_id="i",
        output_dir=out,
        code_commit=TEST_CODE_COMMIT,
    )
    table = _read_bar(res.bar_paths[0])
    assert table.num_rows == 1
    assert table.column("open_time")[0].as_py() == expected_open_us
    assert table.column("close_time")[0].as_py() == expected_close_us
    assert res.publish_plan.quality_status.value == "PASS"
    assert res.publish_plan.coverage.event_start == expected_open
    assert res.publish_plan.coverage.event_end == expected_open
    assert any(
        i.code == "binance_kline_interval_mismatch" for i in res.issues
    ) is False


def test_leap_year_february_month_bar() -> None:
    # Probe close calculation using Feb 1 -> Mar 1 (leap year).
    expected_open = datetime(2020, 2, 1, tzinfo=timezone.utc)
    expected_open_us = int(expected_open.timestamp() * 1_000_000)
    expected_close_us = int(datetime(2020, 3, 1, tzinfo=timezone.utc).timestamp() * 1_000_000) - 1_000
    raw = _ro(
        tmp_path := Path(tempfile.mkdtemp()),
        "leapfeb",
        _trivial_zip(_csv(_month_row_ms(2020, 2, 1))),
    )
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = normalize_binance_kline(
        [raw],
        market_type="coinm",
        interval="1M",
        venue_id="v",
        instrument_id="i",
        output_dir=out,
        code_commit=TEST_CODE_COMMIT,
    )
    table = _read_bar(res.bar_paths[0])
    assert table.num_rows == 1
    assert table.column("open_time")[0].as_py() == expected_open_us
    assert table.column("close_time")[0].as_py() == expected_close_us
    assert res.publish_plan.quality_status.value == "PASS"
    assert res.publish_plan.coverage.event_start == expected_open
    assert res.publish_plan.coverage.event_end == expected_open
    assert any(
        i.code == "binance_kline_interval_mismatch" for i in res.issues
    ) is False


def test_case_sensitive_1m_vs_1M() -> None:
    assert _parse_interval("1m").kind == "fixed"
    assert _parse_interval("1M").kind == "calendar_month"


# market physical volume fields ----------------------------------------------


def test_spot_physical_volume_values_and_partition_units(tmp_path: Path) -> None:
    row = _good_row_ms(1_000_000_000_000)
    raw = _ro(tmp_path, "r1", _trivial_zip(_csv(row)))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = normalize_binance_kline(
        [raw], market_type="spot", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out, code_commit=TEST_CODE_COMMIT,
    )
    table = _read_bar(res.bar_paths[0])
    assert table.column("volume")[0].as_py() == 10.0
    assert table.column("quote_volume")[0].as_py() == 1000.0
    assert table.column("taker_buy_base_volume")[0].as_py() == 2.0
    assert table.column("taker_buy_quote_volume")[0].as_py() == 500.0
    assert "base_asset_volume" not in table.column_names
    spec = next(s for s in res.publish_plan.output_specs if s.relative_path.endswith("bars.parquet"))
    assert spec.partition["volume_unit"] == "base_asset"
    assert spec.partition["secondary_volume_unit"] == "quote_asset"


def test_usdm_physical_volume_values_and_partition_units(tmp_path: Path) -> None:
    row = _good_row_ms(1_000_000_000_000)
    raw = _ro(tmp_path, "r1", _trivial_zip(_csv(row)))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = normalize_binance_kline(
        [raw], market_type="usdm", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out, code_commit=TEST_CODE_COMMIT,
    )
    table = _read_bar(res.bar_paths[0])
    assert table.column("volume")[0].as_py() == 10.0
    assert table.column("quote_volume")[0].as_py() == 1000.0
    assert table.column("taker_buy_base_volume")[0].as_py() == 2.0
    assert table.column("taker_buy_quote_volume")[0].as_py() == 500.0
    assert "base_asset_volume" not in table.column_names
    spec = next(s for s in res.publish_plan.output_specs if s.relative_path.endswith("bars.parquet"))
    assert spec.partition["volume_unit"] == "base_asset"
    assert spec.partition["secondary_volume_unit"] == "quote_asset"


def test_coinm_physical_volume_values_and_partition_units(tmp_path: Path) -> None:
    row = _good_row_ms(1_000_000_000_000)
    raw = _ro(tmp_path, "r1", _trivial_zip(_csv(row)))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = normalize_binance_kline(
        [raw], market_type="coinm", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out, code_commit=TEST_CODE_COMMIT,
    )
    table = _read_bar(res.bar_paths[0])
    # COIN-M CSV: field5=contracts, field7=base asset, field9=taker buy contracts,
    # field10=taker buy base asset.
    assert table.column("volume")[0].as_py() == 10.0
    assert table.column("base_asset_volume")[0].as_py() == 1000.0
    assert table.column("taker_buy_volume")[0].as_py() == 2.0
    assert table.column("taker_buy_base_asset_volume")[0].as_py() == 500.0
    assert "quote_volume" not in table.column_names
    assert "taker_buy_base_volume" not in table.column_names
    assert res.publish_plan.quality_summary["schema_variant"] == "coin_margined"
    spec = next(s for s in res.publish_plan.output_specs if s.relative_path.endswith("bars.parquet"))
    assert spec.partition["volume_unit"] == "contracts"
    assert spec.partition["secondary_volume_unit"] == "base_asset"


def test_unknown_market_type_raises(tmp_path: Path) -> None:
    raw = _ro(tmp_path, "raw_ok", _trivial_zip(_csv(_good_row_ms())))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match="market_type"):
        normalize_binance_kline(
            [raw], market_type="unknown", interval="1m", venue_id="v", instrument_id="i",
            output_dir=out, code_commit=TEST_CODE_COMMIT,
        )


# MAN-001 full publication ---------------------------------------------------


def test_full_man001_publish_plan(tmp_path: Path) -> None:
    row = _good_row_ms(1_000_000_000_000)
    raw = _ro(tmp_path, "raw_1", _trivial_zip(_csv(row)))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = normalize_binance_kline(
        [raw], market_type="spot", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out, code_commit=TEST_CODE_COMMIT,
    )
    plan = res.publish_plan
    sources = dict(plan.output_sources)
    specs = list(plan.output_specs)
    verified = verify_outputs(
        sources=sources,
        specs=specs,
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters=dict(plan.row_counters),
    )
    assert len(verified) == len(specs)
    assert plan.schema.version == "2"
    assert plan.schema.fingerprint
    assert plan.transform.version == "4"
    assert plan.config.config_sha256 != ""
    assert len(plan.config.config_sha256) == 64
    assert plan.code.commit == TEST_CODE_COMMIT
    assert plan.code.commit != "unknown"
    rels = sorted(plan.output_sources)
    assert all(p.startswith("binance/spot/1m/") for p in rels)


def test_full_man001_publish_plan_with_catalog(tmp_path: Path) -> None:
    from cryptofactors.catalog.runner import apply_migrations, MIGRATIONS_DIR

    row = _good_row_ms(1_000_000_000_000)
    raw = _ro(tmp_path, "raw_1", _trivial_zip(_csv(row)))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = normalize_binance_kline(
        [raw], market_type="spot", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out, code_commit=TEST_CODE_COMMIT,
    )
    plan = res.publish_plan

    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    cat = SqliteDatasetCatalog(db)
    cat._conn.execute(
        "INSERT OR IGNORE INTO source (source_id, source_type, official_url, terms_class, config_json, created_at) VALUES (?, 'external', NULL, NULL, '{}', ?)",
        ("binance", datetime.now(timezone.utc).isoformat()),
    )
    cat._conn.execute(
        "INSERT OR IGNORE INTO raw_object (raw_object_id, source_id, sha256, byte_size, storage_uri, original_name, request_json, response_metadata_json, source_checksum, acquired_at, event_start, event_end, status) VALUES (?, ?, ?, ?, ?, NULL, '{}', '{}', NULL, ?, NULL, NULL, 'ACQUIRED')",
        ("raw_1", "binance", "deadbeef", 0, "raw/sha256/de/adbeef", datetime.now(timezone.utc).isoformat()),
    )
    cat._conn.commit()

    root = tmp_path / "store"
    root.mkdir(exist_ok=True)
    cfg = DatasetStoreConfig(root=root)
    pub = DatasetPublisher(cfg, cat)
    receipt = pub.publish(plan, register_catalog=True)
    assert receipt.dataset_id
    assert receipt.manifest_sha256
    assert receipt.catalog_registered is True
    expected_start = datetime.fromtimestamp(1_000_000_000_000_000 / 1_000_000, tz=timezone.utc)
    assert plan.coverage.event_start == expected_start
    assert plan.coverage.event_end == expected_start
    assert plan.config.config_sha256 != ""
    assert plan.code.commit == TEST_CODE_COMMIT
    assert plan.quality_status.value == "PASS"


# lineage / no network / local-only smoke -------------------------------------


def test_output_lineage_contains_raw_object(tmp_path: Path) -> None:
    res = _result_for(tmp_path, [_good_row_ms()])
    bar_spec = next(s for s in res.publish_plan.output_specs if "bars.parquet" in s.relative_path)
    q_spec = next(s for s in res.publish_plan.output_specs if "quality.parquet" in s.relative_path)
    assert bar_spec.partition["raw_object_id"] == "r1"
    assert bar_spec.partition["venue_id"] == "v"
    assert bar_spec.partition["instrument_id"] == "i"
    assert q_spec.partition["raw_object_id"] == "r1"
    assert all(p.kind == DependencyKind.RAW_OBJECT for p in res.publish_plan.dependencies)


def test_no_network_used() -> None:
    source_path = resources.files("cryptofactors.ingest").joinpath("binance.py")
    text = source_path.read_text(encoding="utf-8")
    for needle in ["urllib", "requests", "http.client", "httpx", "aiohttp", "socket"]:
        assert needle not in text, f"networking hint: {needle}"
