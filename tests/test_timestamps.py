"""Focused tests for timestamp inference."""

import pytest
from source_audit.timestamps import infer_timestamp_unit
from source_audit.errors import AmbiguousTimestampError


def test_seconds():
    assert infer_timestamp_unit(1735689600).unit == "s"


def test_milliseconds():
    assert infer_timestamp_unit(1735689600000).unit == "ms"


def test_microseconds():
    assert infer_timestamp_unit(1735689600000000).unit == "us"


def test_nanoseconds():
    assert infer_timestamp_unit(1735689600000000000).unit == "ns"


def test_ambiguous_raises():
    with pytest.raises(AmbiguousTimestampError):
        infer_timestamp_unit(1234567890)  # could be s or ms in some ranges


def test_string_input():
    assert infer_timestamp_unit("1735689600000").unit == "ms"
