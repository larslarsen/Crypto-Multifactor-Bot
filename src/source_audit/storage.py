"""Storage statistics and explicit-assumption projections (U25 / U50 / U100)."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, ROUND_HALF_EVEN

from .errors import AuditError, InvalidNumericError
from .models import ProjectionAssumptions, StorageSample, StorageStats


def _require_nonneg_int(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidNumericError(f"{name} must be a non-negative int")
    return value


def _bytes_per_row(sample: StorageSample, *, basis: str) -> Decimal:
    if sample.row_count <= 0:
        raise AuditError(
            f"Sample {sample.label!r} has non-positive row_count",
            context={"row_count": sample.row_count},
        )
    if basis == "compressed":
        if sample.compressed_bytes < 0:
            raise InvalidNumericError("compressed_bytes must be >= 0")
        return Decimal(sample.compressed_bytes) / Decimal(sample.row_count)
    if basis == "extracted":
        if sample.extracted_bytes < 0:
            raise InvalidNumericError("extracted_bytes must be >= 0")
        return Decimal(sample.extracted_bytes) / Decimal(sample.row_count)
    raise AuditError(
        f"Unknown basis {basis!r}; expected 'compressed' or 'extracted'"
    )


def _quantile(sorted_values: Sequence[Decimal], q: Decimal) -> Decimal:
    """Inclusive linear interpolation quantile for Decimal samples."""
    if not sorted_values:
        raise AuditError("Cannot compute quantile of empty sample set")
    if q < 0 or q > 1:
        raise InvalidNumericError("quantile must be in [0, 1]")
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    pos = q * Decimal(n - 1)
    lo = int(pos.to_integral_value(rounding=ROUND_HALF_EVEN))
    hi = min(lo + 1, n - 1)
    frac = pos - Decimal(lo)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def compute_storage_stats(
    samples: Sequence[StorageSample],
    *,
    basis: str,
    upper_quantile: Decimal,
    stress_case_bytes_per_row: Decimal,
    projection_assumptions: ProjectionAssumptions,
) -> StorageStats:
    """Compute bytes-per-row statistics and U25/U50/U100 projections.

    Projections are produced **only** from ``projection_assumptions``. No universe
    size, frequency, or retention defaults are embedded in this function.
    """
    if not samples:
        raise AuditError("At least one storage sample is required")
    if basis not in ("compressed", "extracted"):
        raise AuditError("basis must be 'compressed' or 'extracted'")
    if not isinstance(upper_quantile, Decimal):
        raise InvalidNumericError("upper_quantile must be a Decimal in (0, 1]")
    if upper_quantile <= 0 or upper_quantile > 1:
        raise InvalidNumericError("upper_quantile must be in (0, 1]")
    if not isinstance(stress_case_bytes_per_row, Decimal):
        raise InvalidNumericError("stress_case_bytes_per_row must be a Decimal")
    if stress_case_bytes_per_row < 0:
        raise InvalidNumericError("stress_case_bytes_per_row must be >= 0")

    pa = projection_assumptions
    if pa.basis not in ("compressed", "extracted"):
        raise AuditError("projection_assumptions.basis must be 'compressed' or 'extracted'")
    if pa.basis != basis:
        raise AuditError(
            "projection_assumptions.basis must match the stats basis",
            context={"stats_basis": basis, "projection_basis": pa.basis},
        )
    _require_nonneg_int("universe_size", pa.universe_size)
    _require_nonneg_int("rows_per_asset_per_period", pa.rows_per_asset_per_period)
    _require_nonneg_int("retention_periods", pa.retention_periods)
    for name, val in (
        ("replication_factor", pa.replication_factor),
        ("overhead_multiplier", pa.overhead_multiplier),
        ("safety_multiplier", pa.safety_multiplier),
    ):
        if not isinstance(val, Decimal) or val < 0:
            raise InvalidNumericError(f"{name} must be a non-negative Decimal")

    bpr_map: dict[str, Decimal] = {}
    values: list[Decimal] = []
    labels: list[str] = []
    for sample in samples:
        bpr = _bytes_per_row(sample, basis=basis)
        if sample.label in bpr_map:
            raise AuditError(f"Duplicate sample label: {sample.label}")
        bpr_map[sample.label] = bpr
        values.append(bpr)
        labels.append(sample.label)

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 1:
        med = sorted_vals[n // 2]
    else:
        med = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / Decimal(2)

    upper = _quantile(sorted_vals, upper_quantile)
    max_obs = sorted_vals[-1]

    def _project(universe: int, bpr: Decimal) -> Decimal:
        rows = (
            Decimal(universe)
            * Decimal(pa.rows_per_asset_per_period)
            * Decimal(pa.retention_periods)
        )
        return (
            rows
            * bpr
            * pa.replication_factor
            * pa.overhead_multiplier
            * pa.safety_multiplier
        )

    # U25 / U50 / U100 are 25%, 50%, 100% of the caller-supplied universe_size.
    u_full = pa.universe_size
    projections = {
        "U25": _project(max(u_full // 4, 0), upper),
        "U50": _project(max(u_full // 2, 0), upper),
        "U100": _project(u_full, upper),
        "U100_stress": _project(u_full, stress_case_bytes_per_row),
    }

    return StorageStats(
        samples_used=tuple(labels),
        bytes_per_row_by_sample=bpr_map,
        median_bytes_per_row=med,
        upper_quantile_bytes_per_row=upper,
        max_observed_bytes_per_row=max_obs,
        stress_case_bytes_per_row=stress_case_bytes_per_row,
        upper_quantile=upper_quantile,
        projections=projections,
        projection_assumptions=pa,
        basis=basis,
    )
