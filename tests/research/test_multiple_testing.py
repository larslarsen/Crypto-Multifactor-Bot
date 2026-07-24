"""EXP-008 regression tests for multiple-testing correction functions."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# The correction functions live in a research runner script.
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "research"))
from run_multiple_testing_analysis import (
    _benjamini_hochberg,
    _block_bootstrap_returns,
    _bonferroni_correction,
    _hansen_spa,
    _individual_bootstrap_pvalue,
    _white_reality_check,
)


def test_bonferroni_rejects_when_expected() -> None:
    p_values = np.array([0.001, 0.02, 0.05, 0.1])
    result = _bonferroni_correction(p_values, alpha=0.05)
    assert result["method"] == "Bonferroni"
    assert result["m"] == 4
    assert result["threshold"] == 0.05 / 4
    assert result["rejected"] == [True, False, False, False]
    assert np.allclose(result["adjusted_p_values"], np.minimum(p_values * 4, 1.0))


def test_benjamini_hochberg_rejects_sorted_p_values() -> None:
    # Three small p-values should survive BH with alpha=0.05
    p_values = np.array([0.01, 0.02, 0.03, 0.5, 0.6])
    result = _benjamini_hochberg(p_values, alpha=0.05)
    assert result["method"] == "Benjamini-Hochberg"
    assert len(result["q_values"]) == 5
    assert result["rejected"].count(True) == 3
    # The largest p-value should have q >= its own p-value
    assert result["q_values"][-1] >= p_values[-1]


def test_block_bootstrap_preserves_length() -> None:
    returns = np.array([0.01, -0.01, 0.02, -0.02, 0.015, -0.015])
    totals = _block_bootstrap_returns(returns, n_iterations=100, block_size=2, rng=np.random.default_rng(42))
    assert totals.shape == (100,)


def test_individual_bootstrap_pvalue_extreme_returns() -> None:
    # Very strong positive returns -> low p-value
    rng = np.random.default_rng(42)
    returns = np.full(50, 0.05)
    p_value = _individual_bootstrap_pvalue(returns, observed_total=5.0, n_iterations=500, block_size=4, rng=rng)
    assert 0.0 < p_value <= 0.05

    # Near-zero returns -> high p-value
    returns = np.random.normal(0, 0.01, size=50)
    p_value = _individual_bootstrap_pvalue(returns, observed_total=0.05, n_iterations=500, block_size=4, rng=rng)
    assert p_value > 0.05


def test_white_reality_check_p_value_bounds() -> None:
    rng = np.random.default_rng(42)
    n_configs, n_periods = 5, 30
    returns_matrix = np.random.normal(0, 0.02, size=(n_configs, n_periods))
    observed_totals = np.expm1(np.sum(np.log1p(returns_matrix), axis=1))
    factor_ids = [f"cfg_{i}" for i in range(n_configs)]
    result = _white_reality_check(returns_matrix, observed_totals, factor_ids, 200, 4, rng)
    assert 0.0 < result["bootstrap_p_value"] <= 1.0
    assert result["best_config_factor_id"] in factor_ids


def test_hansen_spa_p_value_bounds() -> None:
    rng = np.random.default_rng(42)
    n_configs, n_periods = 5, 30
    returns_matrix = np.random.normal(0, 0.02, size=(n_configs, n_periods))
    observed_totals = np.expm1(np.sum(np.log1p(returns_matrix), axis=1))
    result = _hansen_spa(returns_matrix, observed_totals, 200, 4, rng)
    assert 0.0 < result["bootstrap_p_value"] <= 1.0
    assert "benchmark_total_return" in result


def test_white_reality_check_rejects_with_one_outlier() -> None:
    rng = np.random.default_rng(42)
    n_configs, n_periods = 5, 30
    # Four configs are pure noise, one config has a strong positive drift
    returns_matrix = np.random.normal(0, 0.01, size=(n_configs, n_periods))
    returns_matrix[0] = np.random.normal(0.02, 0.01, size=n_periods)
    observed_totals = np.expm1(np.sum(np.log1p(returns_matrix), axis=1))
    factor_ids = [f"cfg_{i}" for i in range(n_configs)]
    result = _white_reality_check(returns_matrix, observed_totals, factor_ids, 500, 4, rng)
    assert result["best_config_index"] == 0
    assert result["best_config_factor_id"] == "cfg_0"
    # Best config should have a small p-value (survives reality check)
    assert result["bootstrap_p_value"] < 0.10


def test_hansen_spa_rejects_with_one_outlier() -> None:
    rng = np.random.default_rng(42)
    n_configs, n_periods = 5, 30
    returns_matrix = np.random.normal(0, 0.01, size=(n_configs, n_periods))
    returns_matrix[0] = np.random.normal(0.02, 0.01, size=n_periods)
    observed_totals = np.expm1(np.sum(np.log1p(returns_matrix), axis=1))
    result = _hansen_spa(returns_matrix, observed_totals, 500, 4, rng)
    assert result["best_config_index"] == 0
    assert result["bootstrap_p_value"] < 0.10
