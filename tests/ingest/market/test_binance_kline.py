"""Focused BIN-001 regressions against normalizer v2.

Covers the ticket's required cases with the v2 inclusive-close, UTC-microsecond,
duplicate/gap, market-semantics, and MAN-001-publishable behavior.
"""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from cryptofactors.audit.models import IssueSeverity
from cryptofactors.catalog.dataset.models import RowCountPolicy
from cryptofactors.catalog.dataset.outputs import verify_outputs
from cryptofactors.contracts import RawObject
from cryptofactors.ingest.binance import (
    BINANCE_KLINE_TRANSFORM_VERSION,
    normalize_binance_kline,
)

# Binance kline CSV field order (12 fields, headerless or first row data):
# 0 open_time 1 open 2 high 3 low 4 close 5 volume 6 close_time
# 7 quote_volume 8 trades 9 taker_buy_base_volume 10 taker_buy_quote_volume 11 ignore


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


def _csv(*rows: list[str]) -> bytes:
    out = io.StringIO()
    for r in rows:
        out.write(",".join(r) + "\n")
    return out.getvalue().encode("utf-8")


def _zip(name: str, csv_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{name}.csv", csv_bytes)
    return buf.getvalue()


def _good_row_ms(open_ms: int, interval_ms: int) -> list[str]:
    close_ms = open_ms + interval_ms - 1
    return [
        str(open_ms),   # open_time
        "95",           # open
        "100",          # high
        "90",           # low
        "98",           # close
        "10",           # volume
        str(close_ms),  # close_time (inclusive)
        "1000",         # quote_volume
        "5",            # trades
        "2",            # taker_buy_base_volume
        "500",          # taker_buy_quote_volume
        "0",            # ignore
    ]


# ---------------------------------------------------------------------------
# transform version
# ---------------------------------------------------------------------------


def test_transform_version_is_two() -> None:
    assert BINANCE_KLINE_TRANSFORM_VERSION == "2"


# ---------------------------------------------------------------------------
# inclusive close + exclusive close
# ---------------------------------------------------------------------------


def test_inclusive_close_ms_no_issue(tmp_path: Path) -> None:
    row = _good_row_ms(1_600_000_000_000, 60_000)
    ro = _ro(tmp_path, "r1", _zip("k", _csv(row)))
    out = tmp_path / "out"
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn", instrument_id="i1", output_dir=out
    )
    assert not any(i.severity is IssueSeverity.ERROR for i in res.issues)
    assert res.publish_plan.quality_status.value == "PASS"


def test_exclusive_close_ms_surfaces_mismatch(tmp_path: Path) -> None:
    open_ms = 1_600_000_000_000
    bad = [
        str(open_ms), "95", "100", "90", "98", "10",
        str(open_ms + 60_000), "1000", "5", "2", "500", "0",  # exclusive close
    ]
    ro = _ro(tmp_path, "r1", _zip("k", _csv(bad)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn", instrument_id="i1", output_dir=tmp_path / "out"
    )
    assert "binance_kline_interval_mismatch" in {i.code for i in res.issues}
    assert res.publish_plan.quality_status.value == "REJECTED"


# ---------------------------------------------------------------------------
# post-2025 us inclusive + normalized timestamps
# ---------------------------------------------------------------------------


def test_inclusive_close_us_no_issue(tmp_path: Path) -> None:
    open_us = 1_700_000_000_000_000
    interval_us = 60_000_000
    close_us = open_us + interval_us - 1
    row = [
        str(open_us), "95", "100", "90", "98", "10",
        str(close_us), "1000", "5", "2", "500", "0",
    ]
    ro = _ro(tmp_path, "us1", _zip("k", _csv(row)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn", instrument_id="i1", output_dir=tmp_path / "out"
    )
    assert not any(i.severity is IssueSeverity.ERROR for i in res.issues)
    bar_spec = next(s for s in res.publish_plan.output_specs if s.relative_path.endswith("bars.parquet"))
    table = pq.read_table(str(res.bar_paths[0]))
    assert table.schema.field("open_time").type == pa.int64()
    assert table.schema.field("close_time").type == pa.int64()
    assert table.column("open_time")[0].as_py() == open_us
    assert table.column("close_time")[0].as_py() == close_us
    assert bar_spec.partition["timestamp_storage"] == "utc_microseconds"


def test_normalized_timestamps_are_utc_us(tmp_path: Path) -> None:
    open_ms = 1_600_000_000_000
    row = _good_row_ms(open_ms, 60_000)
    ro = _ro(tmp_path, "ms1", _zip("k", _csv(row)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn", instrument_id="i1", output_dir=tmp_path / "out"
    )
    bar_spec = next(s for s in res.publish_plan.output_specs if s.relative_path.endswith("bars.parquet"))
    table = pq.read_table(str(res.bar_paths[0]))
    assert table.column("open_time")[0].as_py() == open_ms * 1000
    assert table.column("source_open_time")[0].as_py() == open_ms
    assert bar_spec.partition["timestamp_unit"] == "ms"


# ---------------------------------------------------------------------------
# duplicate / gap
# ---------------------------------------------------------------------------


def test_duplicate_open_time_surfaces_issue(tmp_path: Path) -> None:
    ot = 1_600_000_000_000
    row = _good_row_ms(ot, 60_000)
    ro = _ro(tmp_path, "dup", _zip("k", _csv(row, [row[0][:]] + row[1:])))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn", instrument_id="i1", output_dir=tmp_path / "out"
    )
    assert "binance_kline_duplicate_open_time" in {i.code for i in res.issues}
    bar_spec = next(s for s in res.publish_plan.output_specs if s.relative_path.endswith("bars.parquet"))
    assert bar_spec.rows == 2


def test_gap_surfaces_issue(tmp_path: Path) -> None:
    row_a = _good_row_ms(1_600_000_000_000, 60_000)
    row_b = _good_row_ms(1_600_000_000_000 + 120_000, 60_000)  # skip one minute
    ro = _ro(tmp_path, "gap", _zip("k", _csv(row_a, row_b)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn", instrument_id="i1", output_dir=tmp_path / "out"
    )
    assert "binance_kline_gap" in {i.code for i in res.issues}


def test_cross_object_duplicate(tmp_path: Path) -> None:
    ot = 1_600_000_000_000
    row = _good_row_ms(ot, 60_000)
    ro1 = _ro(tmp_path, "a", _zip("a", _csv(row)))
    ro2 = _ro(tmp_path, "b", _zip("b", _csv(row)))
    res = normalize_binance_kline(
        [ro1, ro2], market_type="spot", interval="1m", venue_id="bn", instrument_id="i1", output_dir=tmp_path / "out"
    )
    assert any(
        i.code == "binance_kline_duplicate_open_time"
        and i.context.get("other_raw_object_id") != i.context.get("this_raw_object_id")
        for i in res.issues
    )


# ---------------------------------------------------------------------------
# market type + volume semantics
# ---------------------------------------------------------------------------


def test_unknown_market_type_raises(tmp_path: Path) -> None:
    ro = _ro(tmp_path, "r1", _zip("k", _csv(_good_row_ms(1_600_000_000_000, 60_000))))
    with pytest.raises(ValueError, match="market_type"):
        normalize_binance_kline([ro], market_type="unknown", interval="1m", venue_id="bn", instrument_id="i1", output_dir=tmp_path / "out")


def test_man001_verify_outputs(tmp_path: Path) -> None:
    row = _good_row_ms(1_600_000_000_000, 60_000)
    ro = _ro(tmp_path, "r1", _zip("k", _csv(row)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn", instrument_id="i1", output_dir=tmp_path / "out"
    )
    bar_specs = [s for s in res.publish_plan.output_specs if s.relative_path.endswith("bars.parquet")]
    assert bar_specs, "bar output spec missing"
    sources = {bar_specs[0].relative_path: res.bar_paths[0]}
    verified = verify_outputs(
        sources=sources,
        specs=bar_specs,
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters=res.publish_plan.row_counters,
    )
    assert len(verified) == len(bar_specs)
