"""Conservative, candidate-based timestamp unit inference."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Union, Dict, Any
from .errors import AmbiguousTimestampError, AuditError


class OutOfRangeTimestampError(AuditError):
    pass


def _safe_to_datetime(value: int, unit: str) -> datetime:
    if unit == "s":
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if unit == "ms":
        return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
    if unit == "us":
        return datetime.fromtimestamp(value / 1_000_000.0, tz=timezone.utc)
    if unit == "ns":
        return datetime.fromtimestamp(value / 1_000_000_000.0, tz=timezone.utc)
    raise ValueError(unit)


def infer_timestamp_unit(
    value: Union[int, float, str, Decimal],
    min_date: datetime = datetime(2010, 1, 1, tzinfo=timezone.utc),
    max_date: datetime = datetime(2030, 1, 1, tzinfo=timezone.utc),
) -> Dict[str, Any]:
    """Candidate validation. Exactly one plausible → return it. Multiple → ambiguous error."""
    # Normalize input
    if isinstance(value, float):
        if not value.is_integer():
            raise AuditError("Non-integer float timestamps rejected to avoid precision loss")
        value = int(value)
    elif isinstance(value, str):
        value = int(value) if '.' not in value else int(Decimal(value))
    elif isinstance(value, Decimal):
        if value % 1 != 0:
            raise AuditError("Non-integer Decimal rejected")
        value = int(value)
    elif not isinstance(value, int):
        raise AuditError(f"Unsupported type: {type(value)}")

    candidates = []
    for unit in ("s", "ms", "us", "ns"):
        try:
            dt = _safe_to_datetime(value, unit)
            if min_date <= dt <= max_date:
                candidates.append((unit, dt))
        except (ValueError, OSError, OverflowError):
            continue

    if len(candidates) == 1:
        unit, dt = candidates[0]
        return {"unit": unit, "datetime": dt, "value": value}
    elif len(candidates) > 1:
        raise AmbiguousTimestampError(f"Multiple units plausible for {value}")
    else:
        raise OutOfRangeTimestampError(f"Value {value} out of range {min_date}–{max_date}")
