"""Focused tests for Binance archive precision comparison (local archives only).

Headerless archives are now supported natively. In headerless mode the caller must
supply ``timestamp_column`` as an integer column index; the reported schema is empty
because there is no header row to inspect.
"""

from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from source_audit.binance_precision import compare_binance_archive_precision
from source_audit.errors import PrecisionComparisonError


def _zip_csv(path: Path, member: str, header: str | None, rows: list[str]) -> None:
    body = ("\n".join(rows) + "\n") if header is None else (header + "\n" + "\n".join(rows) + "\n")
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(member, body.encode("utf-8"))


def _headerless_rows(unit: str, count: int = 7) -> list[str]:
    # aggTrades-like: id,price,quantity,firstTradeId,lastTradeId,time,isBuyerMaker,ignore
    # klines-like: openTime,open,high,low,close,volume,closeTime,assetVolume,trades,takerBuyBase,takerBuyQuote,ignore
    if unit == "s":
        time_base = 1_735_689_600
    elif unit == "ms":
        time_base = 1_735_689_600_000
    else:
        time_base = 1_735_689_600_000_000
    if unit in ("s", "ms"):
        return [f"{i},{100 + i},{1 + i},{1},{1},{time_base + i},False,False" for i in range(1, count + 1)]
    return [f"{i},{100 + i},{1 + i},{1},{1},{time_base + i},{1},{1},{1},{1},{1},False" for i in range(1, count + 1)]


def _bounds() -> tuple[datetime, datetime]:
    return (
        datetime(2010, 1, 1, tzinfo=timezone.utc),
        datetime(2030, 1, 1, tzinfo=timezone.utc),
    )


def test_same_unit_does_not_claim_transition(tmp_path: Path) -> None:
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    rows = [f"{i},1735689600000,{100 + i}" for i in range(1, 8)]
    _zip_csv(a, "BTCUSDT-trades-2025-01-01.csv", "id,time,price", rows)
    _zip_csv(b, "BTCUSDT-trades-2025-01-02.csv", "id,time,price", rows)
    min_utc, max_utc = _bounds()
    result = compare_binance_archive_precision(
        a,
        b,
        timestamp_column="time",
        timestamp_min_utc=min_utc,
        timestamp_max_utc=max_utc,
        min_valid_inferences=5,
    )
    assert result.inferred_unit_a == "ms"
    assert result.inferred_unit_b == "ms"
    assert result.supports_timestamp_precision_transition is False
    assert "same dominant unit" in result.transition_rationale
    assert result.unit_distribution_a.get("ms", 0) >= 5


def test_different_units_support_transition_with_evidence(tmp_path: Path) -> None:
    a = tmp_path / "old.zip"
    b = tmp_path / "new.zip"
    rows_s = [f"{i},{1735689600 + i},100" for i in range(1, 8)]
    rows_ms = [f"{i},{1735689600000 + i * 1000},100" for i in range(1, 8)]
    _zip_csv(a, "old.csv", "id,time,price", rows_s)
    _zip_csv(b, "new.csv", "id,time,price", rows_ms)
    min_utc, max_utc = _bounds()
    result = compare_binance_archive_precision(
        a,
        b,
        timestamp_column="time",
        timestamp_min_utc=min_utc,
        timestamp_max_utc=max_utc,
        member_a="old.csv",
        member_b="new.csv",
        min_valid_inferences=5,
        max_malformed_rate=0.2,
        max_ambiguous_rate=0.1,
    )
    assert result.inferred_unit_a == "s"
    assert result.inferred_unit_b == "ms"
    assert result.supports_timestamp_precision_transition is True
    assert result.valid_inferences_a >= 5
    assert result.valid_inferences_b >= 5
    assert "s" in result.unit_distribution_a
    assert "ms" in result.unit_distribution_b


def test_single_valid_row_does_not_support_transition(tmp_path: Path) -> None:
    a = tmp_path / "old.zip"
    b = tmp_path / "new.zip"
    _zip_csv(a, "old.csv", "id,time,price", ["1,1735689600,100"])
    _zip_csv(b, "new.csv", "id,time,price", ["1,1735689600000,100"])
    min_utc, max_utc = _bounds()
    result = compare_binance_archive_precision(
        a,
        b,
        timestamp_column="time",
        timestamp_min_utc=min_utc,
        timestamp_max_utc=max_utc,
        member_a="old.csv",
        member_b="new.csv",
        min_valid_inferences=5,
    )
    assert result.supports_timestamp_precision_transition is False
    assert "min_valid_inferences" in result.transition_rationale


def test_headerless_supports_transition_agg_trades(tmp_path: Path) -> None:
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    _zip_csv(a, "old.csv", None, _headerless_rows("s"))
    _zip_csv(b, "new.csv", None, _headerless_rows("ms"))
    min_utc, max_utc = _bounds()
    result = compare_binance_archive_precision(
        a,
        b,
        timestamp_column=5,
        timestamp_min_utc=min_utc,
        timestamp_max_utc=max_utc,
        has_header=False,
        member_a="old.csv",
        member_b="new.csv",
        min_valid_inferences=5,
        max_malformed_rate=0.1,
        max_ambiguous_rate=0.05,
    )
    assert result.schema_a == ()
    assert result.schema_b == ()
    assert result.inferred_unit_a == "s"
    assert result.inferred_unit_b == "ms"
    assert result.supports_timestamp_precision_transition is True


def test_headerless_no_transition_when_same_unit_klines(tmp_path: Path) -> None:
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    _zip_csv(a, "old.csv", None, _headerless_rows("us"))
    _zip_csv(b, "new.csv", None, _headerless_rows("us"))
    min_utc, max_utc = _bounds()
    result = compare_binance_archive_precision(
        a,
        b,
        timestamp_column=5,
        timestamp_min_utc=min_utc,
        timestamp_max_utc=max_utc,
        has_header=False,
        member_a="old.csv",
        member_b="new.csv",
        min_valid_inferences=5,
    )
    assert result.schema_a == ()
    assert result.schema_b == ()
    assert result.inferred_unit_a == "us"
    assert result.inferred_unit_b == "us"
    assert result.supports_timestamp_precision_transition is False
    assert "same dominant unit" in result.transition_rationale


def test_headerless_string_column_rejected(tmp_path: Path) -> None:
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    _zip_csv(a, "a.csv", None, _headerless_rows("ms"))
    _zip_csv(b, "b.csv", None, _headerless_rows("ms"))
    min_utc, max_utc = _bounds()
    with pytest.raises(PrecisionComparisonError, match="provide an integer column index"):
        compare_binance_archive_precision(
            a,
            b,
            timestamp_column="time",
            timestamp_min_utc=min_utc,
            timestamp_max_utc=max_utc,
            has_header=False,
            member_a="a.csv",
            member_b="b.csv",
            min_valid_inferences=5,
        )


def test_headerless_out_of_range_index_rejected(tmp_path: Path) -> None:
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    _zip_csv(a, "a.csv", None, _headerless_rows("ms"))
    _zip_csv(b, "b.csv", None, _headerless_rows("ms"))
    min_utc, max_utc = _bounds()
    with pytest.raises(PrecisionComparisonError, match="out of range"):
        compare_binance_archive_precision(
            a,
            b,
            timestamp_column=99,
            timestamp_min_utc=min_utc,
            timestamp_max_utc=max_utc,
            has_header=False,
            member_a="a.csv",
            member_b="b.csv",
            min_valid_inferences=5,
        )


def test_headerless_schema_diff_reported(tmp_path: Path) -> None:
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    rows = [f"{i},1735689600000" for i in range(1, 8)]
    rows_b = [f"{i},1735689600000,1" for i in range(1, 8)]
    _zip_csv(a, "a.csv", None, rows)
    _zip_csv(b, "b.csv", None, rows_b)
    min_utc, max_utc = _bounds()
    result = compare_binance_archive_precision(
        a,
        b,
        timestamp_column=0,
        timestamp_min_utc=min_utc,
        timestamp_max_utc=max_utc,
        has_header=False,
        member_a="a.csv",
        member_b="b.csv",
        min_valid_inferences=5,
    )
    assert result.schema_a == ()
    assert result.schema_b == ()
    assert any(d.field_name == "*" for d in result.schema_differences)
