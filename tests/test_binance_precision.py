"""Focused tests for Binance archive precision comparison (local archives only)."""

from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path

from source_audit.binance_precision import compare_binance_archive_precision


def _zip_csv(path: Path, member: str, header: str, rows: list[str]) -> None:
    body = header + "\n" + "\n".join(rows) + "\n"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(member, body.encode("utf-8"))


def test_same_unit_does_not_claim_transition(tmp_path: Path) -> None:
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    # Both millisecond samples around 2025-01-01.
    _zip_csv(
        a,
        "BTCUSDT-trades-2025-01-01.csv",
        "id,time,price",
        ["1,1735689600000,100", "2,1735689601000,101"],
    )
    _zip_csv(
        b,
        "BTCUSDT-trades-2025-01-02.csv",
        "id,time,price",
        ["1,1735776000000,100", "2,1735776001000,101"],
    )
    min_utc = datetime(2010, 1, 1, tzinfo=timezone.utc)
    max_utc = datetime(2030, 1, 1, tzinfo=timezone.utc)
    result = compare_binance_archive_precision(
        a,
        b,
        timestamp_column="time",
        timestamp_min_utc=min_utc,
        timestamp_max_utc=max_utc,
    )
    assert result.inferred_unit_a == "ms"
    assert result.inferred_unit_b == "ms"
    assert result.supports_timestamp_precision_transition is False
    assert "same dominant unit" in result.transition_rationale


def test_different_units_support_transition(tmp_path: Path) -> None:
    a = tmp_path / "old.zip"
    b = tmp_path / "new.zip"
    # Seconds vs milliseconds — both map into 2010–2030.
    _zip_csv(
        a,
        "old.csv",
        "id,time,price",
        ["1,1735689600,100", "2,1735689700,101"],
    )
    _zip_csv(
        b,
        "new.csv",
        "id,time,price",
        ["1,1735689600000,100", "2,1735689700000,101"],
    )
    min_utc = datetime(2010, 1, 1, tzinfo=timezone.utc)
    max_utc = datetime(2030, 1, 1, tzinfo=timezone.utc)
    result = compare_binance_archive_precision(
        a,
        b,
        timestamp_column="time",
        timestamp_min_utc=min_utc,
        timestamp_max_utc=max_utc,
        member_a="old.csv",
        member_b="new.csv",
    )
    assert result.inferred_unit_a == "s"
    assert result.inferred_unit_b == "ms"
    assert result.supports_timestamp_precision_transition is True
    assert result.schema_a == ("id", "time", "price")
    assert result.representative_raw_a
    assert result.representative_raw_b


def test_schema_difference_reported(tmp_path: Path) -> None:
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    _zip_csv(a, "a.csv", "id,time", ["1,1735689600000"])
    _zip_csv(b, "b.csv", "id,time,qty", ["1,1735689600000,1"])
    min_utc = datetime(2010, 1, 1, tzinfo=timezone.utc)
    max_utc = datetime(2030, 1, 1, tzinfo=timezone.utc)
    result = compare_binance_archive_precision(
        a,
        b,
        timestamp_column="time",
        timestamp_min_utc=min_utc,
        timestamp_max_utc=max_utc,
        member_a="a.csv",
        member_b="b.csv",
    )
    assert any(d.field_name == "qty" for d in result.schema_differences)
