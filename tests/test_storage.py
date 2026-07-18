"""Focused tests for storage statistics and projections."""

from __future__ import annotations

from decimal import Decimal

import pytest

from source_audit.errors import AuditError, InvalidNumericError
from source_audit.models import ProjectionAssumptions, StorageSample
from source_audit.storage import compute_storage_stats


def _sample(label: str, rows: int, compressed: int, extracted: int) -> StorageSample:
    return StorageSample(
        label=label,
        source_identity=f"src:{label}",
        row_count=rows,
        compressed_bytes=compressed,
        extracted_bytes=extracted,
        coverage_note="synthetic",
    )


def test_stats_and_projections() -> None:
    samples = [
        _sample("a", 100, 1000, 5000),
        _sample("b", 200, 3000, 9000),
        _sample("c", 50, 400, 2000),
    ]
    assumptions = ProjectionAssumptions(
        universe_size=100,
        rows_per_asset_per_period=10,
        retention_periods=30,
        replication_factor=Decimal("2"),
        basis="compressed",
        overhead_multiplier=Decimal("1.1"),
        safety_multiplier=Decimal("1.5"),
    )
    stats = compute_storage_stats(
        samples,
        basis="compressed",
        upper_quantile=Decimal("0.9"),
        stress_case_bytes_per_row=Decimal("50"),
        projection_assumptions=assumptions,
    )
    assert stats.median_bytes_per_row > 0
    assert "U25" in stats.projections
    assert "U50" in stats.projections
    assert "U100" in stats.projections
    assert stats.projections["U100"] >= stats.projections["U50"]
    assert stats.projections["U50"] >= stats.projections["U25"]
    assert stats.basis == "compressed"
    # Explicit assumptions only — U100 uses universe_size=100 and upper quantile bpr.
    assert stats.projection_assumptions.universe_size == 100


def test_empty_samples_rejected() -> None:
    with pytest.raises(AuditError):
        compute_storage_stats(
            [],
            basis="compressed",
            upper_quantile=Decimal("0.9"),
            stress_case_bytes_per_row=Decimal("1"),
            projection_assumptions=ProjectionAssumptions(
                universe_size=1,
                rows_per_asset_per_period=1,
                retention_periods=1,
                replication_factor=Decimal("1"),
                basis="compressed",
                overhead_multiplier=Decimal("1"),
                safety_multiplier=Decimal("1"),
            ),
        )


def test_basis_mismatch_rejected() -> None:
    with pytest.raises(AuditError, match="basis"):
        compute_storage_stats(
            [_sample("a", 10, 100, 200)],
            basis="compressed",
            upper_quantile=Decimal("1"),
            stress_case_bytes_per_row=Decimal("20"),
            projection_assumptions=ProjectionAssumptions(
                universe_size=10,
                rows_per_asset_per_period=1,
                retention_periods=1,
                replication_factor=Decimal("1"),
                basis="extracted",
                overhead_multiplier=Decimal("1"),
                safety_multiplier=Decimal("1"),
            ),
        )


def test_invalid_quantile() -> None:
    with pytest.raises(InvalidNumericError):
        compute_storage_stats(
            [_sample("a", 10, 100, 200)],
            basis="compressed",
            upper_quantile=Decimal("0"),
            stress_case_bytes_per_row=Decimal("20"),
            projection_assumptions=ProjectionAssumptions(
                universe_size=10,
                rows_per_asset_per_period=1,
                retention_periods=1,
                replication_factor=Decimal("1"),
                basis="compressed",
                overhead_multiplier=Decimal("1"),
                safety_multiplier=Decimal("1"),
            ),
        )
