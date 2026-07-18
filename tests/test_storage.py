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


def _assumptions(
    *,
    u25: int = 25,
    u50: int = 50,
    u100: int = 100,
    basis: str = "compressed",
) -> ProjectionAssumptions:
    return ProjectionAssumptions(
        u25_universe_size=u25,
        u50_universe_size=u50,
        u100_universe_size=u100,
        rows_per_asset_per_period=10,
        retention_periods=30,
        replication_factor=Decimal("2"),
        basis=basis,
        overhead_multiplier=Decimal("1.1"),
        safety_multiplier=Decimal("1.5"),
    )


def test_stats_and_projections() -> None:
    samples = [
        _sample("a", 100, 1000, 5000),
        _sample("b", 200, 3000, 9000),
        _sample("c", 50, 400, 2000),
    ]
    assumptions = _assumptions(u25=25, u50=50, u100=100)
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
    assert stats.projection_assumptions.u100_universe_size == 100
    assert stats.projection_assumptions.u25_universe_size == 25


def test_explicit_universe_counts_not_percentages() -> None:
    """U25/U50/U100 use explicit counts — not fractions of another universe."""
    samples = [_sample("a", 10, 100, 200)]
    # Non-proportional counts (not 25/50/100 of a base).
    assumptions = ProjectionAssumptions(
        u25_universe_size=7,
        u50_universe_size=40,
        u100_universe_size=200,
        rows_per_asset_per_period=1,
        retention_periods=1,
        replication_factor=Decimal("1"),
        basis="compressed",
        overhead_multiplier=Decimal("1"),
        safety_multiplier=Decimal("1"),
    )
    stats = compute_storage_stats(
        samples,
        basis="compressed",
        upper_quantile=Decimal("1"),
        stress_case_bytes_per_row=Decimal("20"),
        projection_assumptions=assumptions,
    )
    bpr = stats.upper_quantile_bytes_per_row
    assert stats.projections["U25"] == Decimal(7) * bpr
    assert stats.projections["U50"] == Decimal(40) * bpr
    assert stats.projections["U100"] == Decimal(200) * bpr


def test_quantile_uses_mathematical_floor() -> None:
    # Five values: indices 0..4; q=0.5 → pos=2.0 → exact index 2.
    samples = [
        _sample("a", 1, 10, 10),
        _sample("b", 1, 20, 20),
        _sample("c", 1, 30, 30),
        _sample("d", 1, 40, 40),
        _sample("e", 1, 50, 50),
    ]
    stats = compute_storage_stats(
        samples,
        basis="compressed",
        upper_quantile=Decimal("0.5"),
        stress_case_bytes_per_row=Decimal("100"),
        projection_assumptions=ProjectionAssumptions(
            u25_universe_size=1,
            u50_universe_size=1,
            u100_universe_size=1,
            rows_per_asset_per_period=1,
            retention_periods=1,
            replication_factor=Decimal("1"),
            basis="compressed",
            overhead_multiplier=Decimal("1"),
            safety_multiplier=Decimal("1"),
        ),
    )
    assert stats.upper_quantile_bytes_per_row == Decimal(30)


def test_empty_samples_rejected() -> None:
    with pytest.raises(AuditError):
        compute_storage_stats(
            [],
            basis="compressed",
            upper_quantile=Decimal("0.9"),
            stress_case_bytes_per_row=Decimal("1"),
            projection_assumptions=ProjectionAssumptions(
                u25_universe_size=1,
                u50_universe_size=1,
                u100_universe_size=1,
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
                u25_universe_size=10,
                u50_universe_size=10,
                u100_universe_size=10,
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
                u25_universe_size=10,
                u50_universe_size=10,
                u100_universe_size=10,
                rows_per_asset_per_period=1,
                retention_periods=1,
                replication_factor=Decimal("1"),
                basis="compressed",
                overhead_multiplier=Decimal("1"),
                safety_multiplier=Decimal("1"),
            ),
        )
