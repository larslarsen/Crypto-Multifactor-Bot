"""Focused tests for Binance archive precision comparison (local archives only)."""

from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from source_audit.binance_precision import compare_binance_archive_precision
from source_audit.errors import PrecisionComparisonError


def _zip_csv(path: Path, member: str, header: str, rows: list[str]) -> None:
    body = header + "\n" + "\n".join(rows) + "\n"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(member, body.encode("utf-8"))


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


def test_headerless_rejected(tmp_path: Path) -> None:
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    _zip_csv(a, "a.csv", "id,time", ["1,1735689600000"])
    _zip_csv(b, "b.csv", "id,time", ["1,1735689600000"])
    min_utc, max_utc = _bounds()
    with pytest.raises(PrecisionComparisonError, match="Headerless"):
        compare_binance_archive_precision(
            a,
            b,
            timestamp_column="time",
            timestamp_min_utc=min_utc,
            timestamp_max_utc=max_utc,
            has_header=False,
        )


def test_schema_difference_reported(tmp_path: Path) -> None:
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    rows = [f"{i},1735689600000" for i in range(1, 8)]
    rows_b = [f"{i},1735689600000,1" for i in range(1, 8)]
    _zip_csv(a, "a.csv", "id,time", rows)
    _zip_csv(b, "b.csv", "id,time,qty", rows_b)
    min_utc, max_utc = _bounds()
    result = compare_binance_archive_precision(
        a,
        b,
        timestamp_column="time",
        timestamp_min_utc=min_utc,
        timestamp_max_utc=max_utc,
        member_a="a.csv",
        member_b="b.csv",
        min_valid_inferences=5,
    )
    assert any(d.field_name == "qty" for d in result.schema_differences)
