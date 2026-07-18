"""Focused tests for timestamp inference (candidate validation)."""

import pytest
from source_audit.timestamps import infer_timestamp_unit, OutOfRangeTimestampError, AmbiguousTimestampError


def test_seconds():
    result = infer_timestamp_unit(1735689600)
    assert result["unit"] == "s"


def test_milliseconds():
    result = infer_timestamp_unit(1735689600000)
    assert result["unit"] == "ms"


def test_microseconds():
    result = infer_timestamp_unit(1735689600000000)
    assert result["unit"] == "us"


def test_ambiguous_or_out_of_range():
    # 1234567890 may be ambiguous or out of range depending on conversion
    with pytest.raises((AmbiguousTimestampError, OutOfRangeTimestampError)):
        infer_timestamp_unit(1234567890)
