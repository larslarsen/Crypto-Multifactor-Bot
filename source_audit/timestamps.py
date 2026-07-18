"""Conservative timestamp unit inference."""

from datetime import datetime, timezone, timedelta
from typing import Union, Optional
from decimal import Decimal

from .errors import AmbiguousTimestampError
from .models import TimestampInference


def infer_timestamp_unit(
    value: Union[int, float, str, Decimal],
    min_date: datetime = datetime(2010, 1, 1, tzinfo=timezone.utc),
    max_date: datetime = datetime(2030, 1, 1, tzinfo=timezone.utc),
) -> TimestampInference:
    """
    Infer timestamp unit using magnitude and divisibility.
    Returns explicit error on ambiguity instead of guessing.
    """
    if isinstance(value, str):
        try:
            value = int(value) if '.' not in value else float(value)
        except ValueError:
            raise AmbiguousTimestampError(f"Cannot parse timestamp: {value}")

    if isinstance(value, float):
        value = int(value)  # conservative

    if not isinstance(value, (int, Decimal)):
        raise AmbiguousTimestampError(f"Unsupported timestamp type: {type(value)}")

    # Plausible ranges (Unix epoch style)
    if 1_000_000_000 <= value <= 2_000_000_000:  # ~2010-2030 in seconds
        return TimestampInference(unit="s", value=value, inferred_from="magnitude")
    elif 1_000_000_000_000 <= value <= 2_000_000_000_000:  # milliseconds
        return TimestampInference(unit="ms", value=value, inferred_from="magnitude")
    elif 1_000_000_000_000_000 <= value <= 2_000_000_000_000_000:  # microseconds
        return TimestampInference(unit="us", value=value, inferred_from="magnitude")
    elif value > 10**17:  # nanoseconds
        return TimestampInference(unit="ns", value=value, inferred_from="magnitude")

    # Divisibility checks for borderline cases
    if value % 1_000_000_000 == 0 and value // 1_000_000_000 < 2_000_000_000:
        return TimestampInference(unit="s", value=value, inferred_from="divisibility")

    # Ambiguous case
    raise AmbiguousTimestampError(
        f"Ambiguous timestamp unit for value {value}. "
        "Multiple units (s/ms/us/ns) are plausible."
    )
