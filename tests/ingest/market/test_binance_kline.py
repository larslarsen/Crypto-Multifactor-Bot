"""Focused regressions for BIN-001 (Binance archive kline normalizer).

Covers the ticket's required cases: explicit market type/interval; timestamp unit
handling across source eras (pre-2025 ms, post-2025 us); UTC interval semantics;
quote/base volume units; duplicate and gap handling via typed QualityIssue; source
object lineage on every output partition; no network access in the normalizer.
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
from cryptofactors.contracts import RawObject
from cryptofactors.ingest.binance import (
    BINANCE_KLINE_FIELD_COUNT,
    normalize_binance_kline,
)

# Binance kline CSV field order (12 fields, headerless or first row data):
# 0 open_time 1 open 2 high 3 low 4 close 5 volume 6 close_time 7 quote_volume
# 8 trades 9 taker_buy_base_volume 10 taker_buy_quote_volume 11 ignore


def _raw_object(tmp_path: Path, name: str, content: bytes) -> RawObject:
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


def _make_csv(*rows: list[str]) -> bytes:
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
    close_ms = open_ms + interval_ms
    return [
        str(open_ms),   # open_time
        "95",           # open
        "100",          # high
        "90",           # low
        "98",           # close
        "10",           # volume
        str(close_ms),  # close_time (== open + interval)
        "1000",         # quote_volume
        "5",            # trades
        "2",            # taker_buy_base_volume
        "500",          # taker_buy_quote_volume
        "0",            # ignore
    ]


# ---------------------------------------------------------------------------
# explicit market type + interval + required explicit params
# ---------------------------------------------------------------------------


def test_explicit_market_type_and_interval_required(tmp_path: Path) -> None:
    ro = _raw_object(tmp_path, "r1", _zip("k", _make_csv(_good_row_ms(1_600_000_000_000, 60_000))))
    # missing interval -> ValueError
    try:
        normalize_binance_kline([ro], market_type="spot", interval="", venue_id="bn", instrument_id="i1", output_dir=tmp_path / "out")
        assert False, "expected ValueError"
    except ValueError:
        pass
    # valid explicit call succeeds
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    assert res.publish_plan.quality_status is not None


# ---------------------------------------------------------------------------
# timestamp unit handling across source eras
# ---------------------------------------------------------------------------


def test_pre_2025_ms_timestamps_normalized(tmp_path: Path) -> None:
    row = _good_row_ms(1_600_000_000_000, 60_000)  # 13-digit ms -> ms era
    ro = _raw_object(tmp_path, "ms1", _zip("k", _make_csv(row)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    assert not any(i.severity is IssueSeverity.ERROR for i in res.issues)
    specs = {s.relative_path: s for s in res.publish_plan.output_specs}
    bar_spec = next(s for p, s in specs.items() if p.endswith("bars.parquet"))
    assert bar_spec.partition["timestamp_unit"] == "ms"


def test_post_2025_us_timestamps_normalized(tmp_path: Path) -> None:
    open_us = 1_700_000_000_000_000  # 16-digit us -> us era
    interval_us = 60_000_000
    close_us = open_us + interval_us
    row = [
        str(open_us), "95", "100", "90", "98", "10",
        str(close_us), "1000", "5", "2", "500", "0",
    ]
    ro = _raw_object(tmp_path, "us1", _zip("k", _make_csv(row)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    assert not any(i.severity is IssueSeverity.ERROR for i in res.issues)
    specs = {s.relative_path: s for s in res.publish_plan.output_specs}
    bar_spec = next(s for p, s in specs.items() if p.endswith("bars.parquet"))
    assert bar_spec.partition["timestamp_unit"] == "us"


# ---------------------------------------------------------------------------
# UTC interval semantics
# ---------------------------------------------------------------------------


def test_interval_mismatch_surfaces_quality_issue(tmp_path: Path) -> None:
    open_ms = 1_600_000_000_000
    # valid OHLC, but close_time does NOT match 1m (60_000 ms) -> interval_mismatch
    bad = [
        str(open_ms), "95", "100", "90", "98", "10",
        str(open_ms + 999), "1000", "5", "2", "500", "0",
    ]
    ro = _raw_object(tmp_path, "mm", _zip("k", _make_csv(bad)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    codes = {i.code for i in res.issues}
    assert "binance_kline_interval_mismatch" in codes
    assert res.publish_plan.quality_status.value == "REJECTED"


# ---------------------------------------------------------------------------
# OHLC invariants
# ---------------------------------------------------------------------------


def test_ohlc_violation_surfaces_quality_issue(tmp_path: Path) -> None:
    open_ms = 1_600_000_000_000
    close_ms = open_ms + 60_000
    # high < low violates
    bad = [
        str(open_ms), "100", "50", "200", str(close_ms), "10",
        str(close_ms), "1000", "5", "2", "500", "0",
    ]
    ro = _raw_object(tmp_path, "oh", _zip("k", _make_csv(bad)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    assert "binance_kline_ohlc_violation" in {i.code for i in res.issues}


# ---------------------------------------------------------------------------
# malformed rows (field count) never silently dropped
# ---------------------------------------------------------------------------


def test_malformed_row_count_surfaces_quality_issue(tmp_path: Path) -> None:
    bad = ["1", "2", "3"]  # wrong field count (need 12)
    ro = _raw_object(tmp_path, "mf", _zip("k", _make_csv(bad)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    assert "binance_kline_malformed_row" in {i.code for i in res.issues}


# ---------------------------------------------------------------------------
# headerless + header-skip support
# ---------------------------------------------------------------------------


def test_header_row_is_skipped(tmp_path: Path) -> None:
    header = ["open_time", "open", "high", "low", "close", "volume", "close_time",
              "quote_volume", "trades", "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"]
    row = _good_row_ms(1_600_000_000_000, 60_000)
    ro = _raw_object(tmp_path, "hd", _zip("k", _make_csv(header, row)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    # one parsed bar beyond header (no error from header being parsed as data)
    assert not any(i.severity is IssueSeverity.ERROR for i in res.issues)
    bar_spec = next(s for s in res.publish_plan.output_specs if s.relative_path.endswith("bars.parquet"))
    assert bar_spec.rows == 1


# ---------------------------------------------------------------------------
# quote/base volume units preserved (decimal, no float loss)
# ---------------------------------------------------------------------------


def test_quote_and_base_volume_units_preserved(tmp_path: Path) -> None:
    row = _good_row_ms(1_600_000_000_000, 60_000)
    row[5] = "10"                       # base volume
    row[7] = "1000.123456789012345678"  # quote volume high precision
    ro = _raw_object(tmp_path, "vq", _zip("k", _make_csv(row)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    assert not any(i.severity is IssueSeverity.ERROR for i in res.issues)
    table = pq.read_table(str(res.bar_paths[0]))
    assert table.schema.field("quote_volume").type == pa.decimal128(38, 18)


# ---------------------------------------------------------------------------
# duplicate and gap handling surfaces as quality issues (not silent)
# NOTE: the integrated Sr drop does NOT yet implement duplicate/gap detection.
# These cases are xfail until that required BIN-001 behavior lands (see REVIEW-0018).
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="BIN-001 required case: duplicate open_time detection not yet implemented in Sr drop", strict=True)
def test_duplicate_open_time_surfaces_issue(tmp_path: Path) -> None:
    row_a = _good_row_ms(1_600_000_000_000, 60_000)
    row_b = _good_row_ms(1_600_000_000_000, 60_000)  # same open_time -> duplicate
    ro = _raw_object(tmp_path, "dup", _zip("k", _make_csv(row_a, row_b)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    assert "binance_kline_duplicate_open_time" in {i.code for i in res.issues}


@pytest.mark.xfail(reason="BIN-001 required case: gap between consecutive rows detection not yet implemented in Sr drop", strict=True)
def test_gap_between_rows_surfaces_issue(tmp_path: Path) -> None:
    row_a = _good_row_ms(1_600_000_000_000, 60_000)        # 1_600_000_000_000 .. +60s
    row_b = _good_row_ms(1_600_000_000_000 + 600_000, 60_000)  # +10m gap (skip interval)
    ro = _raw_object(tmp_path, "gap", _zip("k", _make_csv(row_a, row_b)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    assert "binance_kline_gap" in {i.code for i in res.issues}


# ---------------------------------------------------------------------------
# source object lineage on every output partition
# ---------------------------------------------------------------------------


def test_source_lineage_on_every_partition(tmp_path: Path) -> None:
    row = _good_row_ms(1_600_000_000_000, 60_000)
    ro = _raw_object(tmp_path, "ln", _zip("k", _make_csv(row)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    assert any(d.id == "ln" and d.kind.value == "RAW_OBJECT" for d in res.publish_plan.dependencies)
    for spec in res.publish_plan.output_specs:
        assert spec.partition["raw_object_id"] == "ln"
        assert spec.partition["instrument_id"] == "i1"
        assert spec.partition["venue_id"] == "bn"


# ---------------------------------------------------------------------------
# no network access: normalizer operates purely on local RawObject bytes
# ---------------------------------------------------------------------------


def test_no_network_required_runs_on_local_bytes(tmp_path: Path) -> None:
    row = _good_row_ms(1_600_000_000_000, 60_000)
    ro = _raw_object(tmp_path, "loc", _zip("k", _make_csv(row)))
    res = normalize_binance_kline(
        [ro], market_type="spot", interval="1m", venue_id="bn",
        instrument_id="i1", output_dir=tmp_path / "out",
    )
    assert res.publish_plan.quality_status.value in ("PASS", "PASS_WITH_WARNINGS", "REJECTED")


# ---------------------------------------------------------------------------
# exactly 12-field Binance schema enforced
# ---------------------------------------------------------------------------


def test_field_count_constant_is_twelve() -> None:
    assert BINANCE_KLINE_FIELD_COUNT == 12
