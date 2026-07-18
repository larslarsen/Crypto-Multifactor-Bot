"""Exact, candidate-based Unix timestamp unit inference.

Units considered: seconds, milliseconds, microseconds, nanoseconds.
Conversion uses integer arithmetic only (no binary floating-point scaling).
Python ``datetime`` stores microsecond resolution; for nanosecond inputs the
returned datetime is floored to whole microseconds while the original integer
value and inferred unit are preserved exactly in the result.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Union

from .errors import (
    AmbiguousTimestampError,
    AuditError,
    InvalidNumericError,
    OutOfRangeTimestampError,
)
from .models import TimestampInference, TimestampUnit

NumericInput = Union[int, float, str, Decimal]

_UNITS: tuple[TimestampUnit, ...] = (
    TimestampUnit.SECONDS,
    TimestampUnit.MILLISECONDS,
    TimestampUnit.MICROSECONDS,
    TimestampUnit.NANOSECONDS,
)

_SCALE_TO_SECONDS_DENOMINATOR: dict[TimestampUnit, int] = {
    TimestampUnit.SECONDS: 1,
    TimestampUnit.MILLISECONDS: 1_000,
    TimestampUnit.MICROSECONDS: 1_000_000,
    TimestampUnit.NANOSECONDS: 1_000_000_000,
}


def _require_aware_utc(name: str, bound: datetime) -> datetime:
    if bound.tzinfo is None:
        raise AuditError(f"{name} must be timezone-aware", context={"bound": str(bound)})
    # Normalize to UTC without changing the instant.
    return bound.astimezone(timezone.utc)


def _normalize_integer_value(
    value: NumericInput,
) -> tuple[int | float | str | Decimal, int]:
    """Return (original_preserved, integer_epoch_value).

    Rejects booleans, NaN/inf, non-integral Decimals/floats/strings, and
    precision-losing floats. Never truncates fractional Decimal via int().
    """
    # bool is a subclass of int — reject explicitly.
    if isinstance(value, bool):
        raise InvalidNumericError("Boolean timestamps are rejected")

    if isinstance(value, int):
        return value, value

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise InvalidNumericError("NaN and infinite float timestamps are rejected")
        # Reject non-integral floats and floats outside exact integer range.
        if not value.is_integer():
            raise InvalidNumericError(
                "Non-integer float timestamps are rejected to avoid precision loss"
            )
        as_int = int(value)
        # Guard large floats that cannot be represented exactly in binary float.
        if float(as_int) != value:
            raise InvalidNumericError(
                "Float timestamp is not exactly representable as an integer"
            )
        return value, as_int

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise InvalidNumericError("Non-finite Decimal timestamps are rejected")
        # Exact integer check without truncation.
        if value != value.to_integral_value():
            raise InvalidNumericError(
                "Non-integer Decimal timestamps are rejected; fractional values are "
                "not truncated"
            )
        as_int = int(value)
        return value, as_int

    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise InvalidNumericError("Empty string timestamp is rejected")
        try:
            dec = Decimal(text)
        except (InvalidOperation, ValueError) as exc:
            raise InvalidNumericError(
                f"String timestamp is not a valid number: {value!r}"
            ) from exc
        if not dec.is_finite():
            raise InvalidNumericError("Non-finite string timestamps are rejected")
        if dec != dec.to_integral_value():
            raise InvalidNumericError(
                "Non-integer string timestamps are rejected; fractional values are "
                "not truncated"
            )
        return value, int(dec)

    raise InvalidNumericError(
        f"Unsupported timestamp type: {type(value).__name__}",
        context={"type": type(value).__name__},
    )


def _datetime_from_unit(value: int, unit: TimestampUnit) -> datetime:
    """Convert an integer epoch value to UTC datetime using integer arithmetic.

    For nanoseconds, the datetime is floored to microsecond resolution; the
    original value remains available on the inference result.
    """
    denom = _SCALE_TO_SECONDS_DENOMINATOR[unit]
    # Integer division into whole seconds and residual sub-second units.
    seconds, remainder = divmod(value, denom)
    if unit is TimestampUnit.SECONDS:
        micros = 0
    elif unit is TimestampUnit.MILLISECONDS:
        micros = remainder * 1_000
    elif unit is TimestampUnit.MICROSECONDS:
        micros = remainder
    else:  # nanoseconds — floor to microseconds (remainder is ns within the second)
        micros = remainder // 1_000

    # Construct without float epoch conversion for the sub-second part.
    # timedelta accepts large second counts safely.
    if seconds >= 0:
        base = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return base + timedelta(seconds=seconds, microseconds=micros)

    # Negative epochs: still integer-safe via timedelta.
    base = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return base + timedelta(seconds=seconds, microseconds=micros)


def infer_timestamp_unit(
    value: NumericInput,
    *,
    min_utc: datetime,
    max_utc: datetime,
) -> TimestampInference:
    """Infer the unique plausible unit for ``value`` within ``[min_utc, max_utc]``.

    Parameters
    ----------
    value:
        Integer epoch quantity (or exact integral string/Decimal/float).
    min_utc / max_utc:
        Inclusive, timezone-aware bounds. Normalized to UTC.

    Returns
    -------
    TimestampInference
        Original value, inferred unit, and UTC datetime.

    Raises
    ------
    AmbiguousTimestampError
        More than one unit is plausible.
    OutOfRangeTimestampError
        No unit is plausible.
    InvalidNumericError / AuditError
        Input or bounds are invalid.
    """
    min_bound = _require_aware_utc("min_utc", min_utc)
    max_bound = _require_aware_utc("max_utc", max_utc)
    if min_bound > max_bound:
        raise AuditError(
            "min_utc must be <= max_utc",
            context={"min_utc": min_bound.isoformat(), "max_utc": max_bound.isoformat()},
        )

    original, integer_value = _normalize_integer_value(value)

    plausible: list[tuple[TimestampUnit, datetime]] = []
    for unit in _UNITS:
        try:
            dt = _datetime_from_unit(integer_value, unit)
        except (OverflowError, ValueError, OSError):
            continue
        if min_bound <= dt <= max_bound:
            plausible.append((unit, dt))

    if len(plausible) == 1:
        unit, dt = plausible[0]
        return TimestampInference(
            original_value=original,
            unit=unit,
            datetime_utc=dt,
        )
    if len(plausible) > 1:
        raise AmbiguousTimestampError(
            f"Multiple units plausible for value {integer_value}",
            context={
                "value": integer_value,
                "units": [u.value for u, _ in plausible],
            },
        )
    raise OutOfRangeTimestampError(
        f"Value {integer_value} out of range for all units",
        context={
            "value": integer_value,
            "min_utc": min_bound.isoformat(),
            "max_utc": max_bound.isoformat(),
        },
    )
