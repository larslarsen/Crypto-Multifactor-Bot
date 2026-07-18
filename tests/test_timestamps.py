"""Focused tests for exact timestamp unit inference."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from source_audit.errors import (
    AmbiguousTimestampError,
    AuditError,
    InvalidNumericError,
    OutOfRangeTimestampError,
)
from source_audit.models import TimestampUnit
from source_audit.timestamps import infer_timestamp_unit

MIN = datetime(2010, 1, 1, tzinfo=timezone.utc)
MAX = datetime(2030, 1, 1, tzinfo=timezone.utc)


def test_seconds() -> None:
    result = infer_timestamp_unit(1735689600, min_utc=MIN, max_utc=MAX)
    assert result.unit is TimestampUnit.SECONDS
    assert result.datetime_utc == datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert result.original_value == 1735689600


def test_milliseconds() -> None:
    result = infer_timestamp_unit(1735689600000, min_utc=MIN, max_utc=MAX)
    assert result.unit is TimestampUnit.MILLISECONDS
    assert result.datetime_utc == datetime(2025, 1, 1, tzinfo=timezone.utc)


def test_microseconds() -> None:
    result = infer_timestamp_unit(1735689600000000, min_utc=MIN, max_utc=MAX)
    assert result.unit is TimestampUnit.MICROSECONDS


def test_nanoseconds() -> None:
    result = infer_timestamp_unit(1735689600000000000, min_utc=MIN, max_utc=MAX)
    assert result.unit is TimestampUnit.NANOSECONDS
    assert result.datetime_utc == datetime(2025, 1, 1, tzinfo=timezone.utc)


def test_ambiguous() -> None:
    # 1_500_000_000 is plausible as seconds (~2017) and might also be
    # out of range as ms depending on bounds — pick a known ambiguous window.
    # Use wide bounds that admit more than one unit for a carefully chosen value.
    wide_min = datetime(1970, 1, 1, tzinfo=timezone.utc)
    wide_max = datetime(2100, 1, 1, tzinfo=timezone.utc)
    # Value that is in-range as both s and ms is rare with crypto bounds;
    # with wide bounds, 1e12 is ms (~2001) and us would be far future...
    # 1_600_000_000 as seconds is 2020; as ms is 1970-01-19 — both in wide range.
    with pytest.raises(AmbiguousTimestampError):
        infer_timestamp_unit(1_600_000_000, min_utc=wide_min, max_utc=wide_max)


def test_out_of_range() -> None:
    with pytest.raises(OutOfRangeTimestampError):
        infer_timestamp_unit(1, min_utc=MIN, max_utc=MAX)


def test_reject_bool() -> None:
    with pytest.raises(InvalidNumericError):
        infer_timestamp_unit(True, min_utc=MIN, max_utc=MAX)  # type: ignore[arg-type]


def test_reject_nan_inf() -> None:
    with pytest.raises(InvalidNumericError):
        infer_timestamp_unit(float("nan"), min_utc=MIN, max_utc=MAX)
    with pytest.raises(InvalidNumericError):
        infer_timestamp_unit(float("inf"), min_utc=MIN, max_utc=MAX)


def test_reject_fractional_decimal() -> None:
    with pytest.raises(InvalidNumericError, match="not truncated"):
        infer_timestamp_unit(Decimal("1.5"), min_utc=MIN, max_utc=MAX)


def test_reject_fractional_string() -> None:
    with pytest.raises(InvalidNumericError, match="not truncated"):
        infer_timestamp_unit("1735689600.5", min_utc=MIN, max_utc=MAX)


def test_accept_integral_string_and_decimal() -> None:
    a = infer_timestamp_unit("1735689600000", min_utc=MIN, max_utc=MAX)
    b = infer_timestamp_unit(Decimal("1735689600000"), min_utc=MIN, max_utc=MAX)
    assert a.unit is TimestampUnit.MILLISECONDS
    assert b.unit is TimestampUnit.MILLISECONDS


def test_reject_naive_bounds() -> None:
    with pytest.raises(AuditError, match="timezone-aware"):
        infer_timestamp_unit(
            1735689600,
            min_utc=datetime(2010, 1, 1),
            max_utc=MAX,
        )


def test_reject_reversed_bounds() -> None:
    with pytest.raises(AuditError, match="min_utc"):
        infer_timestamp_unit(1735689600, min_utc=MAX, max_utc=MIN)


def test_ms_subsecond_exact() -> None:
    # 1735689600123 ms → 2025-01-01 00:00:00.123 UTC
    result = infer_timestamp_unit(1735689600123, min_utc=MIN, max_utc=MAX)
    assert result.unit is TimestampUnit.MILLISECONDS
    assert result.datetime_utc.microsecond == 123_000


def test_reject_non_integer_float() -> None:
    with pytest.raises(InvalidNumericError):
        infer_timestamp_unit(1.5, min_utc=MIN, max_utc=MAX)
