"""Focused production-contract tests for Binance USD-M open-interest normalization."""

from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
import stat
import zipfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from cryptofactors.ingest import binance_usdm_open_interest as oi


HEADER = ",".join(oi.METRICS_FIELDS)


def _utc_ms(token: str) -> int:
    moment = datetime.fromisoformat(token.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return int(moment.timestamp()) * 1000


def _line(
    timestamp: str,
    symbol: str = "BTCUSDT",
    level: str = "100.000000000000000001",
    value: str = "200.000000000000000002",
    optional: tuple[str, str, str, str] = ("1.1", "1.2", "1.3", "1.4"),
) -> str:
    return ",".join((timestamp, symbol, level, value, *optional))


def _zip_bytes(key: str, rows: list[str], *, headed: bool = True, member: str | None = None) -> bytes:
    from io import BytesIO

    target = BytesIO()
    member_name = member or key.rsplit("/", 1)[-1][:-4] + ".csv"
    body = "\n".join(([HEADER] if headed else []) + rows) + "\n"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member_name, body.encode())
    return target.getvalue()


def _source(tmp_path: Path, date: str, rows: list[str], *, symbol: str = "BTCUSDT", headed: bool = True, payload: bytes | None = None) -> oi.RawMetricObject:
    key = f"data/futures/um/daily/metrics/{symbol}/{symbol}-metrics-{date}.zip"
    body = payload if payload is not None else _zip_bytes(key, rows, headed=headed)
    path = tmp_path / f"{symbol}-{date}.zip"
    path.write_bytes(body)
    return oi.RawMetricObject(
        source_key=key,
        path=path,
        source_sha256=hashlib.sha256(body).hexdigest(),
        byte_size=len(body),
        authority="synthetic_accepted_test_authority",
        checksum_authority="synthetic_provider_checksum",
        retrieval_time="2026-09-01T00:00:00Z",
    )


def _table(result: oi.NormalizationResult):
    assert len(result.partitions) == 1
    return pq.read_table(result.partitions[0].parquet_path)


@pytest.mark.parametrize("headed", [True, False])
def test_real_format_headed_and_headerless_metrics(tmp_path: Path, headed: bool) -> None:
    source = _source(tmp_path, "2026-07-01", [_line("2026-07-01 00:00:00")], headed=headed)
    result = oi.normalize_open_interest([source], tmp_path / ".normalized")
    table = _table(result)

    assert table.schema == oi.SCHEMA
    assert table.column("source_row_ordinal").to_pylist() == [0]
    assert table.column("venue_symbol").to_pylist() == ["BTCUSDT"]
    assert table.column("metric_symbol").to_pylist() == ["BTCUSDT"]
    lineage = json.loads(result.partitions[0].lineage_path.read_text())
    assert lineage["raw_objects"][0]["raw_object_ref"] == 0
    assert lineage["raw_objects"][0]["source_key"] == source.source_key
    assert lineage["raw_objects"][0]["source_sha256"] == source.source_sha256
    assert "excluded_source_rows" not in lineage
    assert "collapsed_identical_source_rows" not in lineage


def test_exact_decimal_stock_and_contiguous_change(tmp_path: Path) -> None:
    rows = [
        _line("2026-07-01T00:00:00Z", level="100.000000000000000001", value="200.000000000000000002", optional=("", "1.2", "", "1.4")),
        _line("2026-07-01T00:05:00Z", level="100.000000000000000003", value="200.000000000000000007"),
    ]
    table = _table(oi.normalize_open_interest([_source(tmp_path, "2026-07-01", rows)], tmp_path / ".normalized"))

    assert table.column("sum_open_interest").to_pylist() == [
        Decimal("100.000000000000000001"),
        Decimal("100.000000000000000003"),
    ]
    assert table.column("previous_sum_open_interest").to_pylist() == [None, Decimal("100.000000000000000001")]
    assert table.column("open_interest_change").to_pylist() == [None, Decimal("0.000000000000000002")]
    assert table.column("open_interest_value_change").to_pylist() == [None, Decimal("0.000000000000000005")]
    assert table.column("change_interval_seconds").to_pylist() == [None, 300]
    assert table.column("gap_break_status").to_pylist() == ["first_observation", "contiguous"]
    assert table.column("count_toptrader_long_short_ratio").to_pylist()[0] is None


def test_shuffled_daily_rows_follow_economic_time_and_preserve_ordinals(tmp_path: Path) -> None:
    rows = [
        _line("2026-07-01T00:10:17Z", level="104", value="208"),
        _line("2026-07-01T00:00:17Z", level="100", value="200"),
        _line("2026-07-01T00:05:17Z", level="101", value="202"),
    ]
    table = _table(
        oi.normalize_open_interest(
            [_source(tmp_path, "2026-07-01", rows)],
            tmp_path / ".normalized",
        )
    )

    assert table.column("create_time").to_pylist() == [
        _utc_ms("2026-07-01T00:00:17Z"),
        _utc_ms("2026-07-01T00:05:17Z"),
        _utc_ms("2026-07-01T00:10:17Z"),
    ]
    assert table.column("source_row_ordinal").to_pylist() == [1, 2, 0]
    assert table.column("sum_open_interest").to_pylist() == [
        Decimal("100.000000000000000000"),
        Decimal("101.000000000000000000"),
        Decimal("104.000000000000000000"),
    ]
    assert table.column("previous_sum_open_interest").to_pylist() == [
        None,
        Decimal("100.000000000000000000"),
        Decimal("101.000000000000000000"),
    ]
    assert table.column("open_interest_change").to_pylist() == [
        None,
        Decimal("1.000000000000000000"),
        Decimal("3.000000000000000000"),
    ]
    assert table.column("change_interval_seconds").to_pylist() == [None, 300, 300]
    assert table.column("gap_break_status").to_pylist() == [
        "first_observation",
        "contiguous",
        "contiguous",
    ]


@pytest.mark.parametrize(
    "spill_timestamp",
    ["2026-05-04T00:00:00Z", "2026-05-04T00:00:59Z"],
)
def test_adjacent_midnight_spillover_is_excluded_without_replacing_owned_value(
    tmp_path: Path,
    spill_timestamp: str,
) -> None:
    prior = _source(
        tmp_path,
        "2026-05-02",
        [_line("2026-05-02T23:55:00Z", level="99", value="198")],
    )
    source_day = _source(
        tmp_path,
        "2026-05-03",
        [
            _line("2026-05-03T00:05:00Z", level="101", value="202"),
            _line(spill_timestamp, level="999", value="1998"),
        ],
    )
    next_day = _source(
        tmp_path,
        "2026-05-04",
        [_line("2026-05-04T00:00:00Z", level="107", value="214")],
    )
    result = oi.normalize_open_interest(
        [next_day, source_day, prior],
        tmp_path / ".normalized",
    )
    table = _table(result)

    assert table.column("sum_open_interest").to_pylist() == [
        Decimal("99.000000000000000000"),
        Decimal("101.000000000000000000"),
        Decimal("107.000000000000000000"),
    ]
    assert Decimal("999.000000000000000000") not in table.column(
        "sum_open_interest"
    ).to_pylist()
    assert table.column("source_row_ordinal").to_pylist() == [0, 0, 0]
    assert table.column("open_interest_change").to_pylist() == [None, None, None]
    lineage = json.loads(result.partitions[0].lineage_path.read_text())
    assert lineage["excluded_source_rows"] == [
        {
            "source_key": source_day.source_key,
            "source_sha256": source_day.source_sha256,
            "source_row_ordinal": 1,
            "expected_contract_day": "2026-05-03",
            "observed_create_time_utc": spill_timestamp,
            "reason": oi.ADJACENT_MIDNIGHT_SPILLOVER,
        }
    ]
    gaps = pq.read_table(result.gap_artifact.parquet_path).to_pylist()
    prior_time = table.column("create_time").to_pylist()[0]
    assert any(
        row["native_symbol"] == "BTCUSDT"
        and row["missing_run_start_ms"] == prior_time + 300_000
        and row["missing_run_end_ms"] == prior_time + 300_000
        and row["gap_kind"] == "missing_five_minute_run"
        for row in gaps
    )
    descriptor = json.loads(result.completion_path.read_text())
    assert descriptor["totals"] == {
        "partition_count": 1,
        "physical_source_rows": 4,
        "product_rows": 3,
        "quality_gap_rows": result.gap_artifact.row_count,
        "excluded_source_rows": 1,
        "collapsed_identical_source_rows": 0,
    }


@pytest.mark.parametrize(
    "out_of_day_timestamp",
    ["2026-05-04T00:01:00Z", "2026-05-05T00:00:00Z"],
)
def test_non_midnight_or_nonadjacent_spillover_is_rejected(
    tmp_path: Path,
    out_of_day_timestamp: str,
) -> None:
    source = _source(
        tmp_path,
        "2026-05-03",
        [
            _line("2026-05-03T00:05:00Z"),
            _line(out_of_day_timestamp),
        ],
    )
    with pytest.raises(
        oi.OpenInterestNormalizationError,
        match="outside its source contract-day",
    ):
        oi.normalize_open_interest([source], tmp_path / ".normalized")


def test_second_adjacent_midnight_spillover_is_rejected(tmp_path: Path) -> None:
    source = _source(
        tmp_path,
        "2026-05-03",
        [
            _line("2026-05-03T23:55:00Z"),
            _line("2026-05-04T00:00:00Z"),
            _line("2026-05-04T00:00:59Z"),
        ],
    )
    with pytest.raises(
        oi.OpenInterestNormalizationError,
        match="outside its source contract-day",
    ):
        oi.normalize_open_interest([source], tmp_path / ".normalized")


def test_missing_cadence_breaks_change_without_bridging(tmp_path: Path) -> None:
    rows = [
        _line("2026-07-01T00:00:00Z", level="100", value="200"),
        _line("2026-07-01T00:10:00Z", level="103", value="207"),
        _line("2026-07-01T00:15:00Z", level="105", value="211"),
    ]
    table = _table(oi.normalize_open_interest([_source(tmp_path, "2026-07-01", rows)], tmp_path / ".normalized"))

    assert table.column("gap_break_status").to_pylist() == ["first_observation", "gap_break", "contiguous"]
    assert table.column("change_interval_seconds").to_pylist() == [None, 600, 300]
    assert table.column("previous_sum_open_interest").to_pylist() == [None, None, Decimal("103.000000000000000000")]
    assert table.column("open_interest_change").to_pylist() == [None, None, Decimal("2.000000000000000000")]
    gap_table = pq.read_table(
        oi.normalize_open_interest(
            [_source(tmp_path, "2026-07-02", [
                _line("2026-07-02T00:00:00Z"),
                _line("2026-07-02T00:10:00Z"),
            ])],
            tmp_path / ".gaps",
        ).gap_artifact.parquet_path
    )
    btc = [row for row in gap_table.to_pylist() if row["native_symbol"] == "BTCUSDT"]
    assert len(btc) == 1
    assert btc[0]["expected_grid_count"] == 1
    assert btc[0]["gap_kind"] == "missing_five_minute_run"


@pytest.mark.parametrize("seconds", [301, 599])
def test_short_delayed_interval_breaks_change_without_inventing_gap(
    tmp_path: Path,
    seconds: int,
) -> None:
    start = datetime(2026, 7, 1, 0, 0, 17, tzinfo=UTC)
    delayed = start + timedelta(seconds=seconds)
    rows = [
        _line(start.isoformat().replace("+00:00", "Z"), level="100", value="200"),
        _line(delayed.isoformat().replace("+00:00", "Z"), level="101", value="202"),
    ]
    result = oi.normalize_open_interest(
        [_source(tmp_path, "2026-07-01", rows)],
        tmp_path / ".normalized",
    )
    table = _table(result)

    assert table.column("create_time").to_pylist() == [
        int(start.timestamp()) * 1000,
        int(delayed.timestamp()) * 1000,
    ]
    assert table.column("change_interval_seconds").to_pylist() == [None, seconds]
    assert table.column("gap_break_status").to_pylist() == [
        "first_observation",
        "gap_break",
    ]
    assert table.column("previous_sum_open_interest").to_pylist() == [None, None]
    assert table.column("open_interest_change").to_pylist() == [None, None]
    gaps = pq.read_table(result.gap_artifact.parquet_path).to_pylist()
    assert not [row for row in gaps if row["native_symbol"] == "BTCUSDT"]


def test_off_grid_phase_missing_run_uses_previous_observation_phase(tmp_path: Path) -> None:
    rows = [
        _line("2026-07-01T00:00:17Z"),
        _line("2026-07-01T00:10:17Z", level="101", value="202"),
    ]
    result = oi.normalize_open_interest(
        [_source(tmp_path, "2026-07-01", rows)],
        tmp_path / ".normalized",
    )
    btc = [
        row
        for row in pq.read_table(result.gap_artifact.parquet_path).to_pylist()
        if row["native_symbol"] == "BTCUSDT"
    ]

    assert btc == [
        {
            **oi.native_identity("BTCUSDT"),
            "required_product": oi.PRODUCT,
            "utc_month": "2026-07",
            "missing_run_start_ms": _utc_ms("2026-07-01T00:05:17Z"),
            "missing_run_end_ms": _utc_ms("2026-07-01T00:05:17Z"),
            "expected_grid_count": 1,
            "gap_kind": "missing_five_minute_run",
            "reason": "missing_expected_cadence_between_observations",
        }
    ]


def test_off_grid_phase_gap_is_split_at_utc_month_boundary(tmp_path: Path) -> None:
    january = _source(
        tmp_path,
        "2026-01-31",
        [_line("2026-01-31T23:50:17Z")],
    )
    february = _source(
        tmp_path,
        "2026-02-01",
        [_line("2026-02-01T00:10:17Z", level="101", value="202")],
    )
    result = oi.normalize_open_interest(
        [february, january],
        tmp_path / ".normalized",
    )
    btc = [
        row
        for row in pq.read_table(result.gap_artifact.parquet_path).to_pylist()
        if row["native_symbol"] == "BTCUSDT"
    ]

    assert [
        (
            row["utc_month"],
            row["missing_run_start_ms"],
            row["missing_run_end_ms"],
            row["expected_grid_count"],
        )
        for row in btc
    ] == [
        (
            "2026-01",
            _utc_ms("2026-01-31T23:55:17Z"),
            _utc_ms("2026-01-31T23:55:17Z"),
            1,
        ),
        (
            "2026-02",
            _utc_ms("2026-02-01T00:00:17Z"),
            _utc_ms("2026-02-01T00:05:17Z"),
            2,
        ),
    ]


@pytest.mark.parametrize("date_token", ["2020-09-01", "2021-01-01", "2026-07-01"])
def test_date_only_timestamp_is_preserved_as_utc_midnight(
    tmp_path: Path,
    date_token: str,
) -> None:
    result = oi.normalize_open_interest(
        [_source(tmp_path, date_token, [_line(date_token)])],
        tmp_path / ".normalized",
    )
    assert _table(result).column("create_time").to_pylist() == [_utc_ms(date_token)]


def test_native_symbol_utc_month_partition_preserves_boundary_continuity(tmp_path: Path) -> None:
    january = _source(tmp_path, "2026-01-31", [_line("2026-01-31T23:55:00Z", level="100", value="200")])
    february = _source(tmp_path, "2026-02-01", [_line("2026-02-01T00:00:00Z", level="101", value="202")])
    result = oi.normalize_open_interest([february, january], tmp_path / ".normalized")

    assert [(part.native_symbol, part.utc_month) for part in result.partitions] == [
        ("BTCUSDT", "2026-01"),
        ("BTCUSDT", "2026-02"),
    ]
    february_table = pq.read_table(result.partitions[1].parquet_path)
    assert february_table.column("gap_break_status").to_pylist() == ["contiguous"]
    assert february_table.column("previous_sum_open_interest").to_pylist() == [
        Decimal("100.000000000000000000")
    ]
    assert february_table.column("open_interest_change").to_pylist() == [
        Decimal("1.000000000000000000")
    ]


def test_accepted_hbar_conflict_is_typed_gap_and_breaks_continuity(tmp_path: Path) -> None:
    before = _source(tmp_path, "2026-07-08", [_line("2026-07-08T23:55:00Z", "HBARUSDC")], symbol="HBARUSDC")
    after = _source(tmp_path, "2026-07-10", [_line("2026-07-10T00:00:00Z", "HBARUSDC", "101", "202")], symbol="HBARUSDC")
    result = oi.normalize_open_interest([before, after], tmp_path / ".normalized")
    table = _table(result)

    assert result.gaps == (oi.HBAR_CONFLICT_GAP,)
    assert result.gaps[0].outcome == oi.PROVIDER_CONFLICT_UNAVAILABLE
    assert result.gaps[0].expected_provider_sha256 == oi.HBAR_EXPECTED_SHA256
    assert table.column("gap_break_status").to_pylist() == ["first_observation", "gap_break"]
    assert table.column("open_interest_change").to_pylist() == [None, None]
    lineage = json.loads(result.partitions[0].lineage_path.read_text())
    assert lineage["coverage_gaps"] == [json.loads(json.dumps(oi.asdict(oi.HBAR_CONFLICT_GAP)))]
    gaps = pq.read_table(result.gap_artifact.parquet_path)
    assert gaps.schema == oi.QUALITY_GAP_SCHEMA
    hbar = [row for row in gaps.to_pylist() if row["native_symbol"] == "HBARUSDC"]
    assert hbar == [
        {
            **oi.native_identity("HBARUSDC"),
            "required_product": oi.PRODUCT,
            "utc_month": "2026-07",
            "missing_run_start_ms": oi.HBAR_GAP_START_MS,
            "missing_run_end_ms": oi.HBAR_GAP_END_MS,
            "expected_grid_count": 288,
            "gap_kind": "provider_checksum_conflict_unavailable",
            "reason": oi.PROVIDER_CONFLICT_UNAVAILABLE,
        }
    ]
    gap_lineage = json.loads(result.gap_artifact.lineage_path.read_text())
    assert gap_lineage["hbar_checksum_conflict"]["expected_provider_sha256"] == oi.HBAR_EXPECTED_SHA256


@pytest.mark.parametrize("second_level", ["101", "100.0", '"100"'])
def test_conflicting_duplicate_timestamp_tokens_are_rejected(
    tmp_path: Path,
    second_level: str,
) -> None:
    rows = [
        _line("2026-07-01T00:00:00Z", level="100"),
        _line("2026-07-01T00:00:00Z", level=second_level),
    ]
    with pytest.raises(oi.OpenInterestNormalizationError, match="conflicting source tokens"):
        oi.normalize_open_interest([_source(tmp_path, "2026-07-01", rows)], tmp_path / ".normalized")


def test_cross_source_duplicate_authority_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07-01", [_line("2026-07-01T00:00:00Z")])
    with pytest.raises(oi.OpenInterestNormalizationError, match="repeats an identity"):
        oi.normalize_open_interest([source, source], tmp_path / ".normalized")


def test_576_identical_pair_rows_collapse_to_288_with_exact_lineage(
    tmp_path: Path,
) -> None:
    start = datetime(2020, 9, 1, tzinfo=UTC)
    rows: list[str] = []
    for index in range(288):
        timestamp = (start + timedelta(minutes=5 * index)).isoformat().replace(
            "+00:00",
            "Z",
        )
        row = _line(timestamp, level=str(index + 1), value=str(2 * (index + 1)))
        rows.extend((row, row))
    result = oi.normalize_open_interest(
        [_source(tmp_path, "2020-09-01", rows)],
        tmp_path / ".normalized",
    )
    table = _table(result)
    lineage = json.loads(result.partitions[0].lineage_path.read_text())
    collapsed = lineage["collapsed_identical_source_rows"]

    assert table.num_rows == 288
    assert table.column("source_row_ordinal").to_pylist() == list(range(0, 576, 2))
    assert len(collapsed) == 288
    assert collapsed[0] == {
        "source_key": (
            "data/futures/um/daily/metrics/BTCUSDT/"
            "BTCUSDT-metrics-2020-09-01.zip"
        ),
        "source_sha256": lineage["raw_objects"][0]["source_sha256"],
        "kept_source_row_ordinal": 0,
        "collapsed_source_row_ordinal": 1,
        "observed_create_time_utc": "2020-09-01T00:00:00Z",
        "reason": oi.IDENTICAL_SOURCE_REPEAT,
    }
    assert collapsed[-1]["kept_source_row_ordinal"] == 574
    assert collapsed[-1]["collapsed_source_row_ordinal"] == 575
    assert collapsed[-1]["observed_create_time_utc"] == "2020-09-01T23:55:00Z"
    descriptor = json.loads(result.completion_path.read_text())
    assert descriptor["totals"]["physical_source_rows"] == 576
    assert descriptor["totals"]["product_rows"] == 288
    assert descriptor["totals"]["excluded_source_rows"] == 0
    assert descriptor["totals"]["collapsed_identical_source_rows"] == 288


def test_577th_physical_row_is_rejected_before_publication(tmp_path: Path) -> None:
    row = _line("2026-07-01T00:00:00Z")
    output = tmp_path / ".normalized"
    with pytest.raises(oi.OpenInterestNormalizationError, match="576-row physical bound"):
        oi.normalize_open_interest(
            [_source(tmp_path, "2026-07-01", [row] * 577)],
            output,
        )
    assert not output.exists() or not list(output.rglob("*.parquet"))


@pytest.mark.parametrize(
    "row",
    [
        _line("2026-07-01T00:00:00Z", level="nan"),
        _line("2026-07-01T00:00:00Z", level="1e100"),
        _line("2026-07-01T00:00:00Z", level="-1"),
        _line("2026-07-01T00:00:00Z", value="-1"),
        _line("2026-07-01T00:00:00Z", optional=("-0.1", "1", "1", "1")),
        _line("2026-07-01T00:00:00Z", optional=("1", "-0.1", "1", "1")),
        _line("2026-07-01T00:00:00Z", optional=("1", "1", "-0.1", "1")),
        _line("2026-07-01T00:00:00Z", optional=("1", "1", "1", "-0.1")),
        _line("2026-07-01T00:00:00.001Z"),
        _line("2026-07-01T00:00:00Z", symbol="ETHUSDT"),
        "2026-07-01T00:00:00Z,BTCUSDT,1",
    ],
)
def test_malformed_nonfinite_overflow_and_conflicting_rows_are_rejected(tmp_path: Path, row: str) -> None:
    with pytest.raises(oi.OpenInterestNormalizationError):
        oi.normalize_open_interest([_source(tmp_path, "2026-07-01", [row])], tmp_path / ".normalized")


@pytest.mark.parametrize("member", ["../escape.csv", "/absolute.csv", "nested/file.csv", "wrong.csv"])
def test_unsafe_zip_member_paths_are_rejected(tmp_path: Path, member: str) -> None:
    key = "data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2026-07-01.zip"
    payload = _zip_bytes(key, [_line("2026-07-01T00:00:00Z")], member=member)
    with pytest.raises(oi.OpenInterestNormalizationError):
        oi.normalize_open_interest([_source(tmp_path, "2026-07-01", [], payload=payload)], tmp_path / ".normalized")


def test_symlink_and_multi_member_zips_are_rejected(tmp_path: Path) -> None:
    from io import BytesIO

    target = BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        info = zipfile.ZipInfo("BTCUSDT-metrics-2026-07-01.csv")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, b"target")
    symlink = _source(tmp_path, "2026-07-01", [], payload=target.getvalue())
    with pytest.raises(oi.OpenInterestNormalizationError, match="regular"):
        oi.normalize_open_interest([symlink], tmp_path / ".symlink")

    target = BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("BTCUSDT-metrics-2026-07-01.csv", _line("2026-07-01T00:00:00Z"))
        archive.writestr("extra.csv", "x")
    multiple = _source(tmp_path, "2026-07-01", [], payload=target.getvalue())
    with pytest.raises(oi.OpenInterestNormalizationError, match="exactly one"):
        oi.normalize_open_interest([multiple], tmp_path / ".multiple")


def test_crc_invalid_zip_is_rejected(tmp_path: Path) -> None:
    key = "data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2026-07-01.zip"
    valid = _zip_bytes(key, [_line("2026-07-01T00:00:00Z")], headed=False)
    marker = b"2026-07-01T00:00:00Z"
    # Stored data is easiest to corrupt without damaging the central directory.
    from io import BytesIO

    target = BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("BTCUSDT-metrics-2026-07-01.csv", marker + b",BTCUSDT,100,200,1,1,1,1\n")
    corrupted = bytearray(target.getvalue())
    position = corrupted.index(marker)
    corrupted[position] ^= 1
    source = _source(tmp_path, "2026-07-01", [], payload=bytes(corrupted))
    with pytest.raises(oi.OpenInterestNormalizationError):
        oi.normalize_open_interest([source], tmp_path / ".normalized")
    assert valid  # the normal producer shape itself was constructed successfully


def test_interruption_before_publish_leaves_no_partition_or_lineage(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07-01", [_line("2026-07-01T00:00:00Z")])

    def interrupt(kind: str, _stage: Path, _destination: Path) -> None:
        assert kind == "parquet"
        raise RuntimeError("injected interruption")

    output = tmp_path / ".normalized"
    with pytest.raises(RuntimeError, match="injected"):
        oi.normalize_open_interest([source], output, hooks=oi.PublicationHooks(before_publish=interrupt))
    assert not (output / ".partitions").exists() or not any((output / ".partitions").rglob("*.parquet"))
    assert not (output / ".lineage").exists() or not any((output / ".lineage").rglob("*.json"))


def test_product_completion_descriptor_is_published_last(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07-01", [_line("2026-07-01T00:00:00Z")])

    def interrupt(kind: str, _stage: Path, _destination: Path) -> None:
        if kind == "completion":
            raise RuntimeError("interrupt final descriptor")

    output = tmp_path / ".normalized"
    with pytest.raises(RuntimeError, match="final descriptor"):
        oi.normalize_open_interest(
            [source],
            output,
            hooks=oi.PublicationHooks(before_publish=interrupt),
        )
    assert list((output / ".partitions").rglob("*.parquet"))
    assert list((output / ".quality-gaps").glob("*.parquet"))
    assert not list((output / ".complete").glob("*.json"))


@pytest.mark.parametrize("child", [".staging", ".partitions"])
def test_symlinked_output_children_are_never_followed(tmp_path: Path, child: str) -> None:
    source = _source(tmp_path, "2026-07-01", [_line("2026-07-01T00:00:00Z")])
    output = tmp_path / ".normalized"
    outside = tmp_path / "outside"
    output.mkdir()
    outside.mkdir()
    (output / child).symlink_to(outside, target_is_directory=True)

    with pytest.raises(oi.OpenInterestNormalizationError, match="unsafe"):
        oi.normalize_open_interest([source], output)
    assert not list(outside.iterdir())


def test_deterministic_replay_reuses_byte_identical_artifacts(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07-01", [_line("2026-07-01T00:00:00Z"), _line("2026-07-01T00:05:00Z", level="101")])
    output = tmp_path / ".normalized"
    first = oi.normalize_open_interest([source], output)
    first_parquet = first.partitions[0].parquet_path.read_bytes()
    first_lineage = first.partitions[0].lineage_path.read_bytes()
    first_completion = first.completion_path.read_bytes()
    second = oi.normalize_open_interest([source], output)

    assert second.partitions[0].reused is True
    assert second.partitions[0].parquet_path.read_bytes() == first_parquet
    assert second.partitions[0].lineage_path.read_bytes() == first_lineage
    assert second.partitions[0].parquet_sha256 == hashlib.sha256(first_parquet).hexdigest()
    assert second.partitions[0].lineage_sha256 == hashlib.sha256(first_lineage).hexdigest()
    assert second.completion_reused is True
    assert second.completion_path.read_bytes() == first_completion
    assert second.completion_sha256 == hashlib.sha256(first_completion).hexdigest()
    descriptor = json.loads(first_completion)
    assert descriptor["partitions"][0]["parquet_sha256"] == first.partitions[0].parquet_sha256
    assert descriptor["partitions"][0]["lineage_sha256"] == first.partitions[0].lineage_sha256
    assert descriptor["quality_gap_artifact"]["parquet_sha256"] == first.gap_artifact.parquet_sha256
    assert descriptor["raw_authorities"]["v3_direct_recovery"]["manifest_compressed_sha256"] == oi.ACCEPTED_V3_MANIFEST_SHA256


def test_v3_loader_excludes_only_accepted_conflict_and_binds_safe_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recovery = tmp_path / "recovery"
    key = "data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2026-07-01.zip"
    body = _zip_bytes(key, [_line("2026-07-01T00:00:00Z")])
    path = recovery / key
    path.parent.mkdir(parents=True)
    path.write_bytes(body)
    rows = [
        {"record_type": "row", "record": {"family": oi.FAMILY, "identity": key, "provider_checksum": hashlib.sha256(body).hexdigest(), "current_listed_bytes": len(body)}},
        {"record_type": "row", "record": {"family": oi.FAMILY, "identity": oi.HBAR_CONFLICT_KEY, "provider_checksum": oi.HBAR_EXPECTED_SHA256, "current_listed_bytes": oi.HBAR_LISTED_BYTES}},
    ]
    provisional = tmp_path / "manifest.json.gz"
    with gzip.open(provisional, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    manifest = tmp_path / f"{hashlib.sha256(provisional.read_bytes()).hexdigest()}.json.gz"
    provisional.rename(manifest)
    monkeypatch.setattr(oi, "ACCEPTED_V3_MANIFEST_SHA256", manifest.name.removesuffix(".json.gz"))
    monkeypatch.setattr(oi, "ACCEPTED_V3_ROWS", 2)
    monkeypatch.setattr(oi, "ACCEPTED_V3_BYTES", len(body) + oi.HBAR_LISTED_BYTES)
    monkeypatch.setattr(oi, "ACCEPTED_V3_METRICS_ROWS", 2)
    monkeypatch.setattr(oi, "ACCEPTED_V3_BOOK_TICKER_ROWS", 0)

    loaded = oi.load_v3_recovery_sources(manifest, recovery)
    assert [source.source_key for source in loaded] == [key]
    assert loaded[0].path == path


def test_self_addressed_but_nonaccepted_v3_manifest_is_rejected(tmp_path: Path) -> None:
    recovery = tmp_path / "recovery"
    recovery.mkdir()
    provisional = tmp_path / "substitute.json.gz"
    with gzip.open(provisional, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps({"record_type": "row", "record": {}}) + "\n")
    digest = hashlib.sha256(provisional.read_bytes()).hexdigest()
    manifest = tmp_path / f"{digest}.json.gz"
    provisional.rename(manifest)

    with pytest.raises(oi.OpenInterestNormalizationError, match="accepted authority"):
        oi.load_v3_recovery_sources(manifest, recovery)


@pytest.mark.parametrize(
    "state",
    [oi.OUTCOME_CHECKSUM_VERIFIED, oi.OUTCOME_RETAINED],
)
def test_generation0_accepted_completion_states_pass(state: str) -> None:
    oi._require_accepted_generation0_validation_state(state)


def test_generation0_unknown_completion_state_is_rejected() -> None:
    with pytest.raises(
        oi.OpenInterestNormalizationError,
        match="validation state is not accepted",
    ):
        oi._require_accepted_generation0_validation_state("unknown")


def test_minimal_substitute_generation0_database_is_rejected(tmp_path: Path) -> None:
    key = "data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2026-07-01.zip"
    body = _zip_bytes(key, [_line("2026-07-01T00:00:00Z")])
    digest = hashlib.sha256(body).hexdigest()
    content = tmp_path / "content"
    path = content / digest[:2] / digest
    path.parent.mkdir(parents=True)
    path.write_bytes(body)
    state = tmp_path / "state.sqlite"
    connection = sqlite3.connect(state)
    connection.executescript(
        "CREATE TABLE plan_entry(provider TEXT,identity TEXT,kind TEXT,payload_json TEXT);"
        "CREATE TABLE completion(provider TEXT,identity TEXT,content_sha256 TEXT,listed_bytes INTEGER,retrieved_at TEXT,validation_state TEXT);"
        "CREATE TABLE sidecar_fact(provider TEXT,identity TEXT,provider_checksum TEXT);"
    )
    payload = {"payload": {"family": oi.FAMILY}}
    connection.execute("INSERT INTO plan_entry VALUES(?,?,?,?)", ("binance_vision", key, "binance_object", json.dumps(payload)))
    connection.execute("INSERT INTO completion VALUES(?,?,?,?,?,?)", ("binance_vision", key, digest, len(body), "2026-09-01T00:00:00Z", "checksum_verified"))
    connection.execute("INSERT INTO sidecar_fact VALUES(?,?,?)", ("binance_vision", key, digest))
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeError):
        oi.load_generation0_sources(state, content)


def test_unsealed_generation0_tail_is_rejected() -> None:
    class FakeState:
        def authenticate_schema(self) -> None:
            pass

        def authenticate_domains(self) -> None:
            pass

        def authenticate_singletons(self) -> None:
            pass

        def authenticate_prefix(self) -> None:
            pass

        def _require_runnable_head(self) -> None:
            raise oi.OpenInterestNormalizationError("an unsealed fact tail remains")

    with pytest.raises(oi.OpenInterestNormalizationError, match="unsealed fact tail"):
        oi._require_fixed_generation0_terminal(FakeState())  # type: ignore[arg-type]


def test_output_root_and_nonconsumable_conflict_body_are_refused(tmp_path: Path) -> None:
    ordinary = _source(tmp_path, "2026-07-01", [_line("2026-07-01T00:00:00Z")])
    with pytest.raises(oi.OpenInterestNormalizationError, match="hidden"):
        oi.normalize_open_interest([ordinary], tmp_path / "visible")

    conflict_body = _zip_bytes(oi.HBAR_CONFLICT_KEY, [_line("2026-07-09T00:00:00Z", "HBARUSDC")])
    conflict_path = tmp_path / "conflict.zip"
    conflict_path.write_bytes(conflict_body)
    conflict = oi.RawMetricObject(
        source_key=oi.HBAR_CONFLICT_KEY,
        path=conflict_path,
        source_sha256=hashlib.sha256(conflict_body).hexdigest(),
        byte_size=len(conflict_body),
        authority="evidence_only",
        checksum_authority="none",
    )
    with pytest.raises(oi.OpenInterestNormalizationError, match="not consumable"):
        oi.normalize_open_interest([conflict], tmp_path / ".conflict")
