"""Focused BIN-001 regressions against normalizer v3.

Covers: inclusive-close ms/us, normalized UTC-microsecond timestamps,
within/cross-object duplicate and gap detection, empty/header-only fail-closed,
mixed-unit row normalization + object reject, market-specific physical volume
fields, calendar month case-sensitive interval, invalid timestamp coverage, local-
only MAN-001 publication of the complete returned PublishPlan, and lineage on
every output partition."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.audit.models import IssueSeverity
from cryptofactors.catalog.dataset.models import PublishPlan, RowCountPolicy
from cryptofactors.catalog.dataset.outputs import verify_outputs
from cryptofactors.contracts import RawObject
from cryptofactors.ingest.binance import (
    BinanceKlineNormalizeResult,
    _parse_interval,
    normalize_binance_kline,
)
# helpers
# ---------------------------------------------------------------------------


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
    )


def _publish_plan(res: BinanceKlineNormalizeResult) -> PublishPlan:
    return res.publish_plan


# ---------------------------------------------------------------------------
# transform/schema identity
# ---------------------------------------------------------------------------


def test_transform_and_schema_versions() -> None:
    from cryptofactors.ingest.binance import (
        BINANCE_KLINE_SCHEMA_VERSION,
        BINANCE_KLINE_TRANSFORM_VERSION,
    )

    assert BINANCE_KLINE_TRANSFORM_VERSION == "3"
    assert BINANCE_KLINE_SCHEMA_VERSION == "2"


# ---------------------------------------------------------------------------
# inclusive close ms/us
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# normalized UTC-microsecond timestamps
# ---------------------------------------------------------------------------


def test_normalized_timestamps_are_utc_us(tmp_path: Path) -> None:
    res = _result_for(tmp_path, [_good_row_ms(1_600_000_000_000)])
    table = pq.read_table(str(res.bar_paths[0]))
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


# ---------------------------------------------------------------------------
# per-row unit; mixed units reject object
# ---------------------------------------------------------------------------


def test_mixed_units_reject_object_each_row_normalized(tmp_path: Path) -> None:
    ms_row = _good_row_ms(1_600_000_000_000)
    us_row = [
        str(1_600_000_000_000_000), "95", "100", "90", "98", "10",
        str(1_600_000_000_060_000 - 1), "1000", "5", "2", "500", "0",
    ]
    res = _result_for(tmp_path, [ms_row, us_row])
    codes = {i.code for i in res.issues}
    assert "binance_kline_mixed_timestamp_unit" in codes
    assert res.publish_plan.quality_status.value == "REJECTED"


def test_invalid_open_time_surfaces_issue(tmp_path: Path) -> None:
    bad = [
        "9999999999999999", "95", "100", "90", "98", "10",
        "9999999999999999", "1000", "5", "2", "500", "0",
    ]
    res = _result_for(tmp_path, [bad])
    assert "binance_kline_invalid_timestamp" in {i.code for i in res.issues}


# ---------------------------------------------------------------------------
# within + cross-object duplicate/gap
# ---------------------------------------------------------------------------


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
        output_dir=out,
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
        output_dir=out,
    )
    assert any(
        i.code == "binance_kline_duplicate_open_time"
        and i.context.get("scope") == "cross_object"
        and i.context.get("first_raw_object_id") != i.context.get("raw_object_id")
        for i in res.issues
    )


# ---------------------------------------------------------------------------
# empty / header-only fail closed
# ---------------------------------------------------------------------------


def test_empty_archive_fails_closed(tmp_path: Path) -> None:
    raw = _ro(tmp_path, "empty", b"PK\x05\x06" + b"\x00" * 18)
    res = normalize_binance_kline(
        [raw],
        market_type="spot",
        interval="1m",
        venue_id="v",
        instrument_id="i",
        output_dir=tmp_path / "out",
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
    )
    assert "binance_kline_empty_observations" in {i.code for i in res.issues}
    assert res.publish_plan.quality_status.value == "REJECTED"


# ---------------------------------------------------------------------------
# malformed first row
# ---------------------------------------------------------------------------


def test_malformed_first_row_not_silent_header(tmp_path: Path) -> None:
    bad = ["1", "2", "3"]
    res = _result_for(tmp_path, [bad])
    assert "binance_kline_malformed_row" in {i.code for i in res.issues}


# ---------------------------------------------------------------------------
# calendar month + interval case-sensitivity
# ---------------------------------------------------------------------------


def test_calendar_month_1M_and_alias_1mo() -> None:

    spec = _parse_interval("1M")
    assert spec.kind == "calendar_month"
    assert spec.label == "1M"
    assert spec.months == 1

    spec2 = _parse_interval("1mo")
    assert spec2.kind == "calendar_month"
    assert spec2.label == "1M"


def test_case_sensitive_1m_vs_1M() -> None:

    assert _parse_interval("1m").kind == "fixed"
    assert _parse_interval("1M").kind == "calendar_month"


# ---------------------------------------------------------------------------
# market physical volume fields
# ---------------------------------------------------------------------------


def test_spot_volume_columns(tmp_path: Path) -> None:
    res = _result_for(tmp_path, [_good_row_ms()])
    table = pq.read_table(str(res.bar_paths[0]))
    names = table.column_names
    assert "volume" in names
    assert "quote_volume" in names
    assert "taker_buy_base_volume" in names
    assert "taker_buy_quote_volume" in names
    assert "base_asset_volume" not in names


def test_coinm_physical_volume_columns(tmp_path: Path) -> None:
    raw = _ro(tmp_path, "r1", _trivial_zip(_csv(_good_row_ms())))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = normalize_binance_kline(
        [raw], market_type="coinm", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out,
    )
    table = pq.read_table(str(res.bar_paths[0]))
    names = table.column_names
    assert "base_asset_volume" in names
    assert "quote_volume" not in names
    assert res.publish_plan.quality_summary["schema_variant"] == "coin_margined"


def test_unknown_market_type_raises(tmp_path: Path) -> None:
    raw = _ro(tmp_path, "raw_ok", _trivial_zip(_csv(_good_row_ms())))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match="market_type"):
        normalize_binance_kline(
            [raw], market_type="unknown", interval="1m", venue_id="v", instrument_id="i",
            output_dir=out,
        )


# ---------------------------------------------------------------------------
# MAN-001 full publication (bars + quality) of returned PublishPlan
# ---------------------------------------------------------------------------


def test_full_man001_publish_plan(tmp_path: Path) -> None:
    row = _good_row_ms(1_600_000_000_000)
    raw = _ro(tmp_path, "raw_1", _trivial_zip(_csv(row)))
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    res = normalize_binance_kline(
        [raw], market_type="spot", interval="1m", venue_id="v", instrument_id="i",
        output_dir=out,
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
    assert plan.transform.version == "3"
    rels = sorted(plan.output_sources)
    assert all(p.startswith("binance/spot/1m/") for p in rels)


# ---------------------------------------------------------------------------
# lineage / no network / local-only smoke
# ---------------------------------------------------------------------------


def test_output_lineage_contains_raw_object(tmp_path: Path) -> None:
    res = _result_for(tmp_path, [_good_row_ms()])
    bar_spec = next(s for s in res.publish_plan.output_specs if "bars.parquet" in s.relative_path)
    q_spec = next(s for s in res.publish_plan.output_specs if "quality.parquet" in s.relative_path)
    assert bar_spec.partition["raw_object_id"] == "r1"
    assert bar_spec.partition["venue_id"] == "v"
    assert bar_spec.partition["instrument_id"] == "i"
    assert q_spec.partition["raw_object_id"] == "r1"


def test_no_network_used() -> None:
    src = Path("/home/lars/Crypto_Multifactor_Bot/src/cryptofactors/ingest/binance.py").read_text()
    for needle in ["urllib", "requests", "http.client", "httpx", "aiohttp", "socket"]:
        assert needle not in src, f"networking hint: {needle}"
