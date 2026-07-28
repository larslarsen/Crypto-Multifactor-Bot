"""EXP-009 — Pre-registered tsmom_365_30 unit tests.

Covers the frozen identity, 26-Friday holdout calendar, prospective holdout
gate (including wall-clock clamps), stationary bootstrap, accept/reject rule,
required artifact schema, and runner entry-point fail-closed behaviour.
Does not open a real holdout or touch production bars.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from cryptofactors.experiments.exp009 import (
    ACCEPT_ALPHA,
    ACCEPT_MIN_NET_RETURN,
    ARTIFACT_RELATIVE_PATH,
    BAR_PANEL_DATASET_ID,
    BOOTSTRAP_MEAN_BLOCK_LENGTH,
    BOOTSTRAP_N_RESAMPLES,
    BOOTSTRAP_SEED,
    CONFIG_VERSION,
    DATA_LOCK_DATE,
    EXPERIMENT_ID,
    EXPLORATION_END,
    EXPLORATION_START,
    FACTOR_ID,
    FEATURE_VERSION,
    FEE_RATE,
    FINGERPRINT,
    HOLDOUT_END,
    HOLDOUT_START,
    INITIAL_CASH,
    LOOKBACK_DAYS,
    MAX_GROSS,
    MAX_SINGLE_WEIGHT,
    MODEL_ARTIFACT_ID,
    REBALANCE_SCHEDULE,
    REQUIRED_HOLDOUT_DECISIONS,
    RISK_ENFORCEMENT,
    SKIP_DAYS,
    SLIPPAGE_RATE,
    UNIVERSE_DATASET_ID,
    EXP009Error,
    EXP009HoldoutNotReadyError,
    EXP009Mode,
    EXP009Runner,
    HypothesisVerdict,
    _validate_required_artifact_fields,
    apply_decision_rule,
    assess_holdout_readiness,
    build_artifact,
    ensure_model_paper_approved,
    exploration_decision_times,
    friday_decision_times,
    frozen_cost_risk_block,
    frozen_factor_block,
    frozen_statistical_protocol_block,
    get_executing_source_commit,
    holdout_decision_times,
    recompute_holdout_statistics,
    require_clean_source_tree,
    require_holdout_calendar_timestamps,
    require_holdout_ready,
    require_signed_dataset_ids,
    risk_summary_from_period_logs,
    run_readiness_checks,
    stationary_bootstrap_indices,
    stationary_bootstrap_mean_pvalue,
    weekly_net_returns_from_period_logs,
)
from cryptofactors.execution.live import MAX_GROSS_LEVERAGE, MAX_SINGLE_ASSET_WEIGHT
from cryptofactors.execution.paper_loop import PaperLoopPeriodLog, PaperLoopResult
from cryptofactors.factors.tsmom import (
    TSMOM_365_30_FACTOR_ID,
    make_tsmom_365_30,
)
from cryptofactors.universe.binding import (
    BINDING_EVIDENCE_SERIES_KEY,
    DATA011_QUALITY_BAR_PANEL_DATASET_ID,
    PAPER_PANEL_SURVIVORSHIP_POLICY,
    UNIVERSE_BINDING_CODE_VERSION,
)

# Pinned digest of the frozen pre-registration identity (datasets, binding
# policy/version, risk enforcement, rebalance, costs, bootstrap, p-formula,
# thresholds). Recompute when FINGERPRINT inputs change.
_PINNED_FINGERPRINT = (
    "64f709eca95b5f1d7e26218156f0b429377c7cf29d18989a878fd86c0692f8d0"
)

# Wall clock after the full holdout has elapsed (for tests that open the gate).
_POST_HOLDOUT_NOW = datetime(2027, 1, 23, 0, 0, 0, tzinfo=UTC)
# Must match executing source (git HEAD) — not an arbitrary hex string.
_VALID_CODE_COMMIT = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], text=True
).strip().lower()


# ---------------------------------------------------------------------------
# Frozen identity (signed pre-registration)
# ---------------------------------------------------------------------------


def test_frozen_factor_identity() -> None:
    assert EXPERIMENT_ID == "EXP-009"
    assert FACTOR_ID == "tsmom_365_30" == TSMOM_365_30_FACTOR_ID
    assert MODEL_ARTIFACT_ID == "mod_tsmom_365_30_exp009"
    assert LOOKBACK_DAYS == 365
    assert SKIP_DAYS == 30
    assert FEATURE_VERSION == "feat_tsmom_365_30_exp009"
    assert CONFIG_VERSION == "cfg_tsmom_365_30_exp009"
    assert FINGERPRINT == _PINNED_FINGERPRINT
    assert len(FINGERPRINT) == 64


def test_frozen_datasets_and_policy_pins() -> None:
    assert BAR_PANEL_DATASET_ID == DATA011_QUALITY_BAR_PANEL_DATASET_ID
    assert UNIVERSE_DATASET_ID == (
        "ds_22d2100a575a9764cceec9cc75f45867047969d1b348fd630771bfb083f5b3d8"
    )
    assert FEE_RATE == 0.0005
    assert SLIPPAGE_RATE == 0.0005
    assert MAX_SINGLE_WEIGHT == MAX_SINGLE_ASSET_WEIGHT == 0.15
    assert MAX_GROSS == MAX_GROSS_LEVERAGE == 1.0
    assert ACCEPT_MIN_NET_RETURN == 0.02
    assert ACCEPT_ALPHA == 0.05
    assert BOOTSTRAP_MEAN_BLOCK_LENGTH == 4
    assert BOOTSTRAP_N_RESAMPLES == 10_000
    assert BOOTSTRAP_SEED == 20260727
    assert RISK_ENFORCEMENT == "clip_and_renormalize"
    assert REBALANCE_SCHEDULE == "weekly_friday_00utc"
    assert ARTIFACT_RELATIVE_PATH.endswith("42_EXP009_PREREGISTERED_TSMOM.json")


def test_frozen_windows() -> None:
    assert DATA_LOCK_DATE == datetime(2026, 7, 27, tzinfo=UTC)
    assert EXPLORATION_START == datetime(2020, 1, 1, tzinfo=UTC)
    assert EXPLORATION_END == datetime(2026, 7, 1, tzinfo=UTC)
    assert HOLDOUT_START == datetime(2026, 7, 31, tzinfo=UTC)
    assert HOLDOUT_END == datetime(2027, 1, 22, tzinfo=UTC)
    assert REQUIRED_HOLDOUT_DECISIONS == 26
    assert HOLDOUT_START > DATA_LOCK_DATE
    assert HOLDOUT_START.weekday() == 4
    assert HOLDOUT_END.weekday() == 4


def test_make_tsmom_365_30_locked_params() -> None:
    class _EmptyStore:
        def latest_available(self, *args: object, **kwargs: object) -> object:
            raise AssertionError("should not be called in constructor")

    factor = make_tsmom_365_30(_EmptyStore(), market_dataset_id="ds_test")
    assert factor.factor_id == "tsmom_365_30"
    assert factor.lookback_days == 365
    assert factor.skip_days == 30


def test_frozen_blocks_match_pre_registration() -> None:
    factor = frozen_factor_block()
    assert factor["lookback_days"] == 365
    assert factor["skip_days"] == 30
    assert factor["parameter_freeze"] is True
    assert factor["formula"] == "log(P[t-30d] / P[t-365d])"
    assert factor["fingerprint"] == _PINNED_FINGERPRINT

    cost = frozen_cost_risk_block()
    assert cost["fee_bps_per_side"] == 5
    assert cost["slippage_bps_per_side"] == 5
    assert cost["max_single_weight"] == 0.15
    assert cost["max_gross_leverage"] == 1.0
    assert cost["enforcement"] == "clip_and_renormalize"

    stats = frozen_statistical_protocol_block()
    assert stats["alpha"] == 0.05
    assert stats["one_sided"] is True
    assert stats["multiple_testing_correction"] is None
    assert stats["test"] == "stationary_block_bootstrap"
    assert stats["mean_block_length_weeks"] == 4
    assert stats["n_resamples"] == 10_000


# ---------------------------------------------------------------------------
# Holdout calendar
# ---------------------------------------------------------------------------


def test_holdout_calendar_is_exactly_26_fridays() -> None:
    times = holdout_decision_times()
    assert len(times) == 26
    assert times[0] == HOLDOUT_START
    assert times[-1] == HOLDOUT_END
    assert all(t.weekday() == 4 for t in times)
    assert all(t.tzinfo is not None for t in times)
    for prev, curr in zip(times[:-1], times[1:], strict=True):
        assert curr - prev == timedelta(days=7)


def test_friday_decision_times_rejects_non_friday_start() -> None:
    with pytest.raises(EXP009Error, match="Friday"):
        friday_decision_times(DATA_LOCK_DATE, HOLDOUT_END, require_friday=True)


def test_exploration_decision_times_stay_before_holdout() -> None:
    times = exploration_decision_times()
    assert times
    assert times[0] >= EXPLORATION_START
    assert times[-1] <= EXPLORATION_END
    assert all(t.weekday() == 4 for t in times)
    assert all(t < HOLDOUT_START for t in times)


def test_exploration_empty_when_window_has_no_friday() -> None:
    start = datetime(2026, 7, 1, tzinfo=UTC)
    end = datetime(2026, 7, 2, tzinfo=UTC)
    assert exploration_decision_times(start=start, end=end) == []


# ---------------------------------------------------------------------------
# Holdout readiness gate (wall-clock + data-lock clamps)
# ---------------------------------------------------------------------------


def test_holdout_sealed_with_no_bar_coverage() -> None:
    readiness = assess_holdout_readiness(now=_POST_HOLDOUT_NOW)
    assert readiness.ready is False
    assert readiness.required_decisions == 26
    assert len(readiness.decision_times) == 26
    assert len(readiness.missing_decision_times) == 26
    assert readiness.latest_available_bar is None


def test_holdout_sealed_when_latest_bar_is_data011_end() -> None:
    latest = datetime(2026, 7, 1, tzinfo=UTC)
    readiness = assess_holdout_readiness(
        latest_available_bar=latest,
        now=_POST_HOLDOUT_NOW,
    )
    assert readiness.ready is False
    assert len(readiness.missing_decision_times) == 26


def test_holdout_sealed_when_latest_at_or_before_data_lock() -> None:
    readiness = assess_holdout_readiness(
        latest_available_bar=DATA_LOCK_DATE,
        now=_POST_HOLDOUT_NOW,
    )
    assert readiness.ready is False
    assert "data lock" in readiness.reason.lower() or "sealed" in readiness.reason.lower()


def test_holdout_raises_when_latest_is_in_the_future() -> None:
    # Claiming HOLDOUT_END coverage before wall clock reaches it is forbidden.
    with pytest.raises(EXP009Error, match="wall clock"):
        assess_holdout_readiness(
            latest_available_bar=HOLDOUT_END,
            now=DATA_LOCK_DATE,  # 2026-07-27; HOLDOUT_END is still future
        )


def test_holdout_raises_when_available_decision_is_in_the_future() -> None:
    with pytest.raises(EXP009Error, match="wall clock"):
        assess_holdout_readiness(
            available_decision_times=[HOLDOUT_START],
            now=DATA_LOCK_DATE,
        )


def test_holdout_sealed_when_partial_coverage() -> None:
    calendar = holdout_decision_times()
    partial = calendar[:10]
    readiness = assess_holdout_readiness(
        available_decision_times=partial,
        now=_POST_HOLDOUT_NOW,
    )
    assert readiness.ready is False
    assert len(readiness.missing_decision_times) == 16
    assert readiness.missing_decision_times[0] == calendar[10]


def test_holdout_ignores_pre_lock_available_decision_times() -> None:
    """Pre-lock Fridays are ignored; they must not permanently seal a full cover.

    Natural call sites pass every bar-store Friday (2020–2026 + holdout). The
    pre-lock noise must not force ready=False when all 26 holdout Fridays are
    present.
    """
    pre_lock = datetime(2026, 7, 24, tzinfo=UTC)  # Friday before lock
    calendar = holdout_decision_times()
    readiness = assess_holdout_readiness(
        available_decision_times=[pre_lock, *calendar],
        now=_POST_HOLDOUT_NOW,
    )
    assert readiness.ready is True
    assert readiness.missing_decision_times == ()


def test_holdout_ready_when_all_26_covered_after_wall_clock() -> None:
    readiness = assess_holdout_readiness(
        latest_available_bar=HOLDOUT_END,
        now=_POST_HOLDOUT_NOW,
    )
    assert readiness.ready is True
    assert readiness.missing_decision_times == ()
    assert readiness.as_dict()["ready"] is True


def test_holdout_ready_when_all_decision_times_supplied_after_wall_clock() -> None:
    calendar = holdout_decision_times()
    readiness = assess_holdout_readiness(
        available_decision_times=calendar,
        now=_POST_HOLDOUT_NOW,
    )
    assert readiness.ready is True
    assert len(readiness.missing_decision_times) == 0


def test_require_holdout_ready_raises_when_sealed() -> None:
    readiness = assess_holdout_readiness(now=_POST_HOLDOUT_NOW)
    with pytest.raises(EXP009HoldoutNotReadyError):
        require_holdout_ready(readiness)


def test_require_holdout_ready_passes_when_open() -> None:
    readiness = assess_holdout_readiness(
        latest_available_bar=HOLDOUT_END,
        now=_POST_HOLDOUT_NOW,
    )
    require_holdout_ready(readiness)


def test_holdout_cannot_open_today_with_future_bar_claim() -> None:
    """Regression: run_holdout(latest_available_bar=HOLDOUT_END) must not open now."""
    with pytest.raises(EXP009Error, match="wall clock"):
        assess_holdout_readiness(latest_available_bar=HOLDOUT_END)


# ---------------------------------------------------------------------------
# Stationary bootstrap
# ---------------------------------------------------------------------------


def test_stationary_bootstrap_indices_length_and_range() -> None:
    rng = np.random.default_rng(42)
    n = 26
    idx = stationary_bootstrap_indices(n, mean_block_length=4, rng=rng)
    assert idx.shape == (n,)
    assert idx.min() >= 0
    assert idx.max() < n


def test_stationary_bootstrap_indices_rejects_bad_args() -> None:
    rng = np.random.default_rng(0)
    with pytest.raises(EXP009Error):
        stationary_bootstrap_indices(0, 4, rng)
    with pytest.raises(EXP009Error):
        stationary_bootstrap_indices(10, 0, rng)


def test_stationary_bootstrap_pvalue_bounds_and_seed_stability() -> None:
    weekly = list(np.random.default_rng(0).normal(0.001, 0.02, size=26))
    a = stationary_bootstrap_mean_pvalue(weekly, n_resamples=300, seed=99)
    b = stationary_bootstrap_mean_pvalue(weekly, n_resamples=300, seed=99)
    assert a["p_value"] == b["p_value"]
    assert a["exceedances"] == b["exceedances"]
    assert 0.0 < a["p_value"] <= 1.0
    assert a["method"] == "stationary_block_bootstrap"
    assert a["one_sided"] is True
    assert a["n_periods"] == 26
    assert a["mean_block_length"] == 4
    assert a["n_resamples"] == 300
    assert a["p_value"] == pytest.approx(
        (a["exceedances"] + 1) / (a["n_resamples"] + 1)
    )
    from cryptofactors.experiments.exp009 import P_VALUE_FORMULA

    assert a["p_value_formula"] == P_VALUE_FORMULA


def test_stationary_bootstrap_strong_positive_mean_low_pvalue() -> None:
    # Noisy positive drift — must not center to the zero series.
    rng = np.random.default_rng(11)
    weekly = list(rng.normal(0.04, 0.01, size=26))
    result = stationary_bootstrap_mean_pvalue(weekly, n_resamples=1000, seed=11)
    assert result["observed_mean_weekly_return"] > 0.03
    assert result["p_value"] <= 0.05


def test_stationary_bootstrap_zero_mean_high_pvalue() -> None:
    weekly = [0.01, -0.01] * 13
    result = stationary_bootstrap_mean_pvalue(weekly, n_resamples=500, seed=3)
    assert result["p_value"] > 0.05


def test_stationary_bootstrap_rejects_empty_or_nonfinite() -> None:
    with pytest.raises(EXP009Error):
        stationary_bootstrap_mean_pvalue([])
    with pytest.raises(EXP009Error):
        stationary_bootstrap_mean_pvalue([0.01, float("nan")])


# ---------------------------------------------------------------------------
# Decision rule
# ---------------------------------------------------------------------------


def test_decision_rule_accept_both_thresholds() -> None:
    result = apply_decision_rule(0.05, 0.01)
    assert result["verdict"] == HypothesisVerdict.ACCEPT.value
    assert result["meets_return_threshold"] is True
    assert result["meets_significance"] is True


def test_decision_rule_reject_return_only() -> None:
    result = apply_decision_rule(0.01, 0.01)
    assert result["verdict"] == HypothesisVerdict.REJECT.value
    assert result["meets_return_threshold"] is False
    assert result["meets_significance"] is True


def test_decision_rule_reject_p_only() -> None:
    result = apply_decision_rule(0.10, 0.20)
    assert result["verdict"] == HypothesisVerdict.REJECT.value
    assert result["meets_return_threshold"] is True
    assert result["meets_significance"] is False


def test_decision_rule_boundary_accept() -> None:
    result = apply_decision_rule(0.02, 0.05)
    assert result["verdict"] == HypothesisVerdict.ACCEPT.value


def test_decision_rule_boundary_reject_just_below_return() -> None:
    result = apply_decision_rule(0.019999, 0.01)
    assert result["verdict"] == HypothesisVerdict.REJECT.value


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------


def test_weekly_net_returns_from_period_logs() -> None:
    logs = [
        SimpleNamespace(equity=101_000.0),
        SimpleNamespace(equity=102_010.0),
        SimpleNamespace(equity=100_000.0),
    ]
    rets = weekly_net_returns_from_period_logs(logs, initial_cash=100_000.0)
    assert len(rets) == 3
    assert rets[0] == pytest.approx(0.01)
    assert rets[1] == pytest.approx(0.01)
    assert rets[2] == pytest.approx((100_000.0 - 102_010.0) / 102_010.0)


def test_weekly_net_returns_empty() -> None:
    assert weekly_net_returns_from_period_logs([], initial_cash=100_000.0) == []


def test_weekly_net_returns_raises_on_nonpositive_prior_equity() -> None:
    logs = [
        SimpleNamespace(equity=0.0),
        SimpleNamespace(equity=1.0),
    ]
    with pytest.raises(EXP009Error, match="non-positive prior equity"):
        weekly_net_returns_from_period_logs(logs, initial_cash=100_000.0)


def test_weekly_net_returns_raises_on_nonpositive_initial_cash() -> None:
    with pytest.raises(EXP009Error, match="initial_cash"):
        weekly_net_returns_from_period_logs(
            [SimpleNamespace(equity=1.0)],
            initial_cash=0.0,
        )


def test_risk_summary_from_period_logs_compliant() -> None:
    logs = [
        SimpleNamespace(target_weights={"A": 0.10, "B": -0.10, "C": 0.05}),
        SimpleNamespace(target_weights={"A": 0.15, "B": -0.15}),
    ]
    summary = risk_summary_from_period_logs(logs)
    assert summary["max_abs_single_weight"] == pytest.approx(0.15)
    assert summary["max_gross_leverage"] == pytest.approx(0.30)
    assert summary["meets_risk_limits"] is True


def test_risk_summary_breach() -> None:
    logs = [SimpleNamespace(target_weights={"A": 0.20, "B": -0.20})]
    summary = risk_summary_from_period_logs(logs)
    assert summary["meets_risk_limits"] is False


# ---------------------------------------------------------------------------
# Artifact schema
# ---------------------------------------------------------------------------


def _minimal_binding_fingerprint(decision_time: datetime) -> dict[str, Any]:
    return {
        "universe_dataset_id": UNIVERSE_DATASET_ID,
        "bar_panel_dataset_id": BAR_PANEL_DATASET_ID,
        "survivorship_policy": PAPER_PANEL_SURVIVORSHIP_POLICY,
        "universe_code_version": UNIVERSE_BINDING_CODE_VERSION,
        "decision_time": decision_time.isoformat(),
        "eligible_count": 10,
        "with_bars_count": 10,
        "excluded_dead_count": 0,
        "panel_count": 22,
    }


def _fake_session_result(
    decision_times: list[datetime],
    *,
    initial_cash: float = 100_000.0,
    equities: list[float] | None = None,
    total_net_return: float | None = None,
) -> PaperLoopResult:
    if equities is None:
        equities = [initial_cash * (1.0 + 0.001 * (i + 1)) for i in range(len(decision_times))]
    logs: list[PaperLoopPeriodLog] = []
    for dt, eq in zip(decision_times, equities, strict=True):
        logs.append(
            PaperLoopPeriodLog(
                decision_time=dt,
                trades_count=2,
                cash=eq * 0.1,
                equity=eq,
                target_weights={"XBTUSD": 0.1, "ETHUSD": -0.1},
                open_positions={},
                binding_fingerprint=_minimal_binding_fingerprint(dt),
            )
        )
    net = (
        total_net_return
        if total_net_return is not None
        else (equities[-1] - initial_cash) / initial_cash
    )
    return PaperLoopResult(
        model_artifact_id=MODEL_ARTIFACT_ID,
        factor_id=FACTOR_ID,
        initial_cash=initial_cash,
        final_cash=equities[-1] * 0.1,
        final_equity=equities[-1],
        total_net_return=net,
        total_trades_executed=2 * len(decision_times),
        period_logs=tuple(logs),
        universe_dataset_id=UNIVERSE_DATASET_ID,
        bar_panel_dataset_id=BAR_PANEL_DATASET_ID,
        survivorship_policy=PAPER_PANEL_SURVIVORSHIP_POLICY,
        universe_code_version=UNIVERSE_BINDING_CODE_VERSION,
    )


def test_build_artifact_required_fields_without_session() -> None:
    readiness = assess_holdout_readiness(now=_POST_HOLDOUT_NOW)
    artifact = build_artifact(
        mode=EXP009Mode.READINESS,
        universe_binding=None,
        readiness=readiness,
        verdict=HypothesisVerdict.SEALED,
    )
    assert artifact["experiment_id"] == "EXP-009"
    assert artifact["factor_id"] == "tsmom_365_30"
    assert artifact["model_artifact_id"] == MODEL_ARTIFACT_ID
    assert artifact["lookback_days"] == 365
    assert artifact["skip_days"] == 30
    assert artifact["universe_dataset_id"] == UNIVERSE_DATASET_ID
    assert artifact["bar_panel_dataset_id"] == BAR_PANEL_DATASET_ID
    assert artifact["survivorship_policy"] == PAPER_PANEL_SURVIVORSHIP_POLICY
    assert artifact["universe_code_version"] == UNIVERSE_BINDING_CODE_VERSION
    assert artifact["survivorship_invalid"] is False
    assert BINDING_EVIDENCE_SERIES_KEY in artifact
    assert artifact["verdict"] == HypothesisVerdict.SEALED.value
    assert artifact["live_eligible"] is False
    assert artifact["holdout"]["ready"] is False
    assert artifact["mode"] == "readiness"


def test_build_artifact_with_session_includes_binding_series() -> None:
    calendar = holdout_decision_times()
    # Mild drawdown path: total net return is negative → REJECT under the
    # pre-registered rule regardless of bootstrap p-value.
    equities = [INITIAL_CASH * (1.0 - 0.001 * (i + 1)) for i in range(len(calendar))]
    session = _fake_session_result(calendar, equities=equities, initial_cash=INITIAL_CASH)
    readiness = assess_holdout_readiness(
        available_decision_times=calendar,
        now=_POST_HOLDOUT_NOW,
    )
    # Terminal REJECT must use recomputed frozen bootstrap, not ad-hoc B/seed.
    stats = recompute_holdout_statistics(session)
    assert session.total_net_return < ACCEPT_MIN_NET_RETURN
    assert stats["verdict"] == HypothesisVerdict.REJECT.value

    artifact = build_artifact(
        mode=EXP009Mode.HOLDOUT,
        universe_binding=None,
        readiness=readiness,
        session_result=session,
        decision_times=calendar,
        bootstrap=stats["bootstrap"],
        decision_rule=stats["decision_rule"],
        verdict=stats["verdict"],
    )
    series = artifact[BINDING_EVIDENCE_SERIES_KEY]
    assert len(series) == 26
    assert series[0]["decision_time"] == calendar[0].isoformat()
    assert series[-1]["decision_time"] == calendar[-1].isoformat()
    assert artifact["session"]["decision_count"] == 26
    assert artifact["session"][BINDING_EVIDENCE_SERIES_KEY] == series
    assert artifact["survivorship_invalid"] is False
    assert artifact["bootstrap"]["method"] == "stationary_block_bootstrap"
    assert artifact["decision_rule"]["verdict"] == "REJECT"


def test_build_artifact_rejects_accept_outside_open_holdout() -> None:
    readiness = assess_holdout_readiness(now=_POST_HOLDOUT_NOW)  # sealed
    with pytest.raises(EXP009Error, match="mode=holdout"):
        build_artifact(
            mode=EXP009Mode.EXPLORATORY,
            universe_binding=None,
            readiness=readiness,
            verdict=HypothesisVerdict.ACCEPT,
        )
    with pytest.raises(EXP009Error, match="mode=holdout"):
        build_artifact(
            mode=EXP009Mode.HOLDOUT,
            universe_binding=None,
            readiness=readiness,  # mode ok but gate sealed
            verdict=HypothesisVerdict.ACCEPT,
        )


def test_build_artifact_accept_requires_complete_holdout_evidence() -> None:
    """ACCEPT without a full calendar-exact session must fail closed."""
    readiness = assess_holdout_readiness(
        latest_available_bar=HOLDOUT_END,
        now=_POST_HOLDOUT_NOW,
    )
    assert readiness.ready is True
    # Open gate alone is not enough.
    with pytest.raises(EXP009Error, match="complete holdout session"):
        build_artifact(
            mode=EXP009Mode.HOLDOUT,
            universe_binding=None,
            readiness=readiness,
            verdict=HypothesisVerdict.ACCEPT,
            decision_rule=apply_decision_rule(0.05, 0.01),
            bootstrap={"p_value": 0.01},
        )


def test_build_artifact_rejects_fabricated_bootstrap_p_value() -> None:
    """Caller-supplied p-value must match recomputed frozen bootstrap."""
    from cryptofactors.experiments.exp009 import clear_recompute_holdout_statistics_cache

    calendar = holdout_decision_times()
    equities = [INITIAL_CASH * (1.0 - 0.001 * (i + 1)) for i in range(len(calendar))]
    session = _fake_session_result(calendar, equities=equities, initial_cash=INITIAL_CASH)
    readiness = assess_holdout_readiness(
        available_decision_times=calendar,
        now=_POST_HOLDOUT_NOW,
    )
    stats = recompute_holdout_statistics(session)
    assert stats["verdict"] == HypothesisVerdict.REJECT.value
    forged_boot = {**stats["bootstrap"], "p_value": 1e-12}
    forged_rule = apply_decision_rule(session.total_net_return, 1e-12)
    # Even if forged p would still REJECT on return threshold, p must match recompute.
    with pytest.raises(EXP009Error, match="recomputed frozen bootstrap|does not match"):
        build_artifact(
            mode=EXP009Mode.HOLDOUT,
            universe_binding=None,
            readiness=readiness,
            session_result=session,
            decision_times=calendar,
            bootstrap=forged_boot,
            decision_rule=forged_rule
            if forged_rule["verdict"] == HypothesisVerdict.REJECT.value
            else stats["decision_rule"],
            verdict=HypothesisVerdict.REJECT,
        )


def test_recompute_holdout_statistics_is_memoized_by_session_content() -> None:
    """Second call on the same session content must not re-bootstrap (cache hit)."""
    from cryptofactors.experiments import exp009 as exp009_mod

    exp009_mod.clear_recompute_holdout_statistics_cache()
    calendar = holdout_decision_times()
    equities = [INITIAL_CASH * (1.0 - 0.001 * (i + 1)) for i in range(len(calendar))]
    session = _fake_session_result(calendar, equities=equities, initial_cash=INITIAL_CASH)

    calls = {"n": 0}
    real = exp009_mod.stationary_bootstrap_mean_pvalue

    def _counting(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        return real(*args, **kwargs)

    with patch.object(exp009_mod, "stationary_bootstrap_mean_pvalue", side_effect=_counting):
        a = exp009_mod.recompute_holdout_statistics(session)
        b = exp009_mod.recompute_holdout_statistics(session)
    assert calls["n"] == 1
    assert a["bootstrap"]["p_value"] == b["bootstrap"]["p_value"]
    assert a["verdict"] == b["verdict"]


def test_recompute_still_rejects_noncanonical_reported_total_on_cache_hit() -> None:
    """Reported total_net_return guard must not be skipped after a bootstrap cache hit."""
    from cryptofactors.experiments import exp009 as exp009_mod

    exp009_mod.clear_recompute_holdout_statistics_cache()
    calendar = holdout_decision_times()
    equities = [INITIAL_CASH * (1.0 - 0.001 * (i + 1)) for i in range(len(calendar))]
    session_ok = _fake_session_result(calendar, equities=equities, initial_cash=INITIAL_CASH)
    exp009_mod.recompute_holdout_statistics(session_ok)  # prime bootstrap cache

    # Same equity path, forged free-standing total — cache key collides.
    session_bad = _fake_session_result(
        calendar,
        equities=equities,
        initial_cash=INITIAL_CASH,
        total_net_return=0.999,
    )
    with pytest.raises(EXP009Error, match="not canonical for the equity path"):
        exp009_mod.recompute_holdout_statistics(session_bad)


def test_recompute_uses_canonical_equity_path_total() -> None:
    from cryptofactors.experiments.exp009 import (
        canonical_total_net_return_from_equity_path,
        clear_recompute_holdout_statistics_cache,
        compound_total_net_return,
    )

    clear_recompute_holdout_statistics_cache()
    calendar = holdout_decision_times()
    equities = [INITIAL_CASH * (1.0 - 0.001 * (i + 1)) for i in range(len(calendar))]
    session = _fake_session_result(calendar, equities=equities, initial_cash=INITIAL_CASH)
    stats = recompute_holdout_statistics(session)
    equity_total = canonical_total_net_return_from_equity_path(session)
    assert stats["canonical_total_net_return"] == pytest.approx(equity_total)
    assert stats["decision_rule"]["total_net_return"] == pytest.approx(equity_total)
    assert compound_total_net_return(stats["weekly_net_returns"]) == pytest.approx(
        equity_total, abs=1e-9
    )
    # Complete frozen bootstrap protocol evidence.
    assert stats["bootstrap"]["seed"] == BOOTSTRAP_SEED
    assert stats["bootstrap"]["n_resamples"] == BOOTSTRAP_N_RESAMPLES
    assert stats["bootstrap"]["mean_block_length"] == BOOTSTRAP_MEAN_BLOCK_LENGTH
    assert "p_value_formula" in stats["bootstrap"]


def test_build_artifact_accept_with_full_holdout_session() -> None:
    calendar = holdout_decision_times()
    # Strong positive path under frozen bootstrap (may still REJECT if p large).
    equities = [INITIAL_CASH * ((1.02) ** (i + 1)) for i in range(len(calendar))]
    session = _fake_session_result(calendar, equities=equities, initial_cash=INITIAL_CASH)
    readiness = assess_holdout_readiness(
        available_decision_times=calendar,
        now=_POST_HOLDOUT_NOW,
    )
    stats = recompute_holdout_statistics(session)
    # Only assert ACCEPT path when the recomputed rule actually accepts.
    if stats["verdict"] != HypothesisVerdict.ACCEPT.value:
        # Still exercise REJECT terminal path with honest recomputed stats.
        artifact = build_artifact(
            mode=EXP009Mode.HOLDOUT,
            universe_binding=None,
            readiness=readiness,
            session_result=session,
            decision_times=calendar,
            bootstrap=stats["bootstrap"],
            decision_rule=stats["decision_rule"],
            verdict=stats["verdict"],
        )
        assert artifact["verdict"] == HypothesisVerdict.REJECT.value
        return

    artifact = build_artifact(
        mode=EXP009Mode.HOLDOUT,
        universe_binding=None,
        readiness=readiness,
        session_result=session,
        decision_times=calendar,
        bootstrap=stats["bootstrap"],
        decision_rule=stats["decision_rule"],
        verdict=HypothesisVerdict.ACCEPT,
    )
    assert artifact["verdict"] == "ACCEPT"
    assert len(artifact["universe_binding_series"]) == 26


def test_build_artifact_synthetic_session_live_gate_not_real_asof() -> None:
    """SYNTHETIC data_mode must not emit live_gate_satisfied via hardcoded real_asof."""
    calendar = holdout_decision_times()[:3]
    # Positive return complete session would trip live_gate under real_asof.
    session = _fake_session_result(
        calendar,
        equities=[101_000.0, 102_000.0, 103_000.0],
        total_net_return=0.03,
    )
    readiness = assess_holdout_readiness(now=_POST_HOLDOUT_NOW)
    artifact = build_artifact(
        mode=EXP009Mode.SYNTHETIC,
        universe_binding=None,
        readiness=readiness,
        session_result=session,
        decision_times=calendar,
        verdict=HypothesisVerdict.EXPLORATORY_ONLY,
    )
    assert artifact["data_mode"] == "synthetic"
    assert artifact["session"]["live_gate_satisfied"] is False


def test_build_artifact_rejects_survivorship_invalid_true() -> None:
    readiness = assess_holdout_readiness(now=_POST_HOLDOUT_NOW)
    artifact = build_artifact(
        mode=EXP009Mode.READINESS,
        universe_binding=None,
        readiness=readiness,
        verdict=HypothesisVerdict.SEALED,
    )
    bad = dict(artifact)
    bad["survivorship_invalid"] = True
    with pytest.raises(EXP009Error, match="survivorship_invalid"):
        _validate_required_artifact_fields(bad)


def test_build_artifact_rejects_reserved_extra_key_collision() -> None:
    readiness = assess_holdout_readiness(now=_POST_HOLDOUT_NOW)
    with pytest.raises(EXP009Error, match="collides"):
        build_artifact(
            mode=EXP009Mode.READINESS,
            universe_binding=None,
            readiness=readiness,
            verdict=HypothesisVerdict.SEALED,
            extra={"factor_id": "hijacked"},
        )


def test_build_artifact_allows_note_and_readiness_extra() -> None:
    readiness = assess_holdout_readiness(now=_POST_HOLDOUT_NOW)
    artifact = build_artifact(
        mode=EXP009Mode.READINESS,
        universe_binding=None,
        readiness=readiness,
        verdict=HypothesisVerdict.SEALED,
        extra={"note": "sealed", "readiness_checks": {"ok": True}},
    )
    assert artifact["note"] == "sealed"
    assert artifact["readiness_checks"] == {"ok": True}


# ---------------------------------------------------------------------------
# Readiness report (no binding)
# ---------------------------------------------------------------------------


def test_run_readiness_checks_without_binding() -> None:
    report = run_readiness_checks(None, now=_POST_HOLDOUT_NOW)
    assert report.binding_ok is False
    assert report.holdout.ready is False
    assert report.checks["pre_registration_signed"] is True
    assert report.checks["factor_frozen"] is True
    assert report.checks["holdout_calendar_26_fridays"] is True
    assert report.checks["holdout_ready"] is False
    assert report.checks["binding_loaded"] is False
    assert report.checks["all_ready_for_holdout_eval"] is False
    d = report.as_dict()
    assert d["holdout"]["required_decisions"] == 26


def test_run_readiness_checks_forwards_now_for_future_bar_probe() -> None:
    """Probe must not throw on future bars when a frozen now is supplied."""
    # With wall clock at data lock, claiming HOLDOUT_END would raise unless
    # the caller can pass a post-holdout now (non-throwing readiness probe).
    report = run_readiness_checks(
        None,
        latest_available_bar=HOLDOUT_END,
        now=_POST_HOLDOUT_NOW,
    )
    assert report.holdout.ready is True


# ---------------------------------------------------------------------------
# EXP009Runner entry points
# ---------------------------------------------------------------------------


def _stub_runner() -> EXP009Runner:
    """Construct a runner with identity checks stubbed to a clean matching HEAD."""
    binding = MagicMock()
    binding.universe_dataset_id = UNIVERSE_DATASET_ID
    binding.bar_panel_dataset_id = BAR_PANEL_DATASET_ID
    binding.survivorship_policy = PAPER_PANEL_SURVIVORSHIP_POLICY
    binding.universe_code_version = UNIVERSE_BINDING_CODE_VERSION

    def _side_effect(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["git", "rev-parse"]:
            return _VALID_CODE_COMMIT + "\n"
        if cmd[:2] == ["git", "status"]:
            return ""
        raise AssertionError(cmd)

    with patch(
        "cryptofactors.experiments.exp009.subprocess.check_output",
        side_effect=_side_effect,
    ):
        return EXP009Runner(
            universe_binding=binding,
            promotion_registry=MagicMock(),
            as_of_store=MagicMock(),
            get_prices_at=lambda dt, univ: {},
            code_commit=_VALID_CODE_COMMIT,
        )


def test_evaluate_holdout_session_requires_external_readiness() -> None:
    runner = _stub_runner()
    session = _fake_session_result(holdout_decision_times())
    with pytest.raises(EXP009Error, match="externally assessed"):
        runner.evaluate_holdout_session(session, readiness=None)


def test_evaluate_holdout_session_does_not_self_certify_from_logs() -> None:
    """A 26-log session alone must not open the gate via omitted readiness."""
    runner = _stub_runner()
    session = _fake_session_result(holdout_decision_times())
    # Explicit sealed readiness even though session has 26 logs.
    sealed = assess_holdout_readiness(now=_POST_HOLDOUT_NOW)
    assert sealed.ready is False
    with pytest.raises(EXP009HoldoutNotReadyError):
        runner.evaluate_holdout_session(session, readiness=sealed)


def test_evaluate_holdout_session_rejects_unfrozen_bootstrap_seed() -> None:
    """Library guard for programmatic callers (not only the CLI seed freeze)."""
    runner = _stub_runner()
    runner.bootstrap_seed = 999
    open_gate = assess_holdout_readiness(
        latest_available_bar=HOLDOUT_END,
        now=_POST_HOLDOUT_NOW,
    )
    assert open_gate.ready is True
    with pytest.raises(EXP009Error, match="frozen"):
        runner.evaluate_holdout_session(
            _fake_session_result(holdout_decision_times()),
            readiness=open_gate,
        )


def test_evaluate_holdout_session_requires_exact_calendar_timestamps() -> None:
    """26 logs on wrong Fridays must not pass — count alone is insufficient."""
    runner = _stub_runner()
    open_gate = assess_holdout_readiness(
        latest_available_bar=HOLDOUT_END,
        now=_POST_HOLDOUT_NOW,
    )
    # Shift every decision one week earlier than the frozen calendar.
    wrong = [t - timedelta(days=7) for t in holdout_decision_times()]
    with pytest.raises(EXP009Error, match="frozen holdout calendar"):
        runner.evaluate_holdout_session(
            _fake_session_result(wrong),
            readiness=open_gate,
        )


def test_holdout_calendar_rejects_noon_on_correct_dates() -> None:
    """Signed decisions are Friday 00:00 UTC — not any instant on that date."""
    calendar = holdout_decision_times()
    noon = [
        t.replace(hour=12, minute=0, second=0, microsecond=0) for t in calendar
    ]
    with pytest.raises(EXP009Error, match="frozen holdout calendar"):
        require_holdout_calendar_timestamps(noon)


def test_runner_rejects_bootstrap_seed_override_at_construction() -> None:
    binding = MagicMock()
    binding.universe_dataset_id = UNIVERSE_DATASET_ID
    binding.bar_panel_dataset_id = BAR_PANEL_DATASET_ID
    with pytest.raises(EXP009Error, match="bootstrap_seed is frozen"):
        EXP009Runner(
            universe_binding=binding,
            promotion_registry=MagicMock(),
            as_of_store=MagicMock(),
            get_prices_at=lambda dt, univ: {},
            code_commit=_VALID_CODE_COMMIT,
            bootstrap_seed=BOOTSTRAP_SEED + 1,
        )


def test_runner_construction_succeeds_with_clean_source_and_matching_head() -> None:
    """Happy path for identity: clean tree + HEAD match → runner constructs."""
    from cryptofactors.experiments.exp009 import EXP009_SOURCE_PATHS

    binding = MagicMock()
    binding.universe_dataset_id = UNIVERSE_DATASET_ID
    binding.bar_panel_dataset_id = BAR_PANEL_DATASET_ID

    def _side_effect(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["git", "rev-parse"]:
            return _VALID_CODE_COMMIT + "\n"
        if cmd[:2] == ["git", "status"]:
            # Clean-tree gate must cover the full first-party closure.
            assert tuple(cmd[cmd.index("--") + 1 :]) == EXP009_SOURCE_PATHS or set(
                cmd[cmd.index("--") + 1 :]
            ) == set(EXP009_SOURCE_PATHS)
            return ""  # clean
        raise AssertionError(cmd)

    with patch(
        "cryptofactors.experiments.exp009.subprocess.check_output",
        side_effect=_side_effect,
    ):
        runner = EXP009Runner(
            universe_binding=binding,
            promotion_registry=MagicMock(),
            as_of_store=MagicMock(),
            get_prices_at=lambda dt, univ: {},
            code_commit=_VALID_CODE_COMMIT,
        )
    assert runner.bootstrap_seed == BOOTSTRAP_SEED
    assert runner.code_commit == _VALID_CODE_COMMIT
    assert "src/cryptofactors/execution/paper_loop.py" in EXP009_SOURCE_PATHS
    assert "src/cryptofactors/universe/binding.py" in EXP009_SOURCE_PATHS


def test_code_identity_rejects_dirty_source_tree() -> None:
    with patch(
        "cryptofactors.experiments.exp009.subprocess.check_output"
    ) as mock_co:
        # First call in get_executing_source_commit (rev-parse), then status.
        def _side_effect(cmd, **kwargs):  # type: ignore[no-untyped-def]
            if cmd[:2] == ["git", "rev-parse"]:
                return _VALID_CODE_COMMIT + "\n"
            if cmd[:2] == ["git", "status"]:
                return " M src/cryptofactors/experiments/exp009.py\n"
            raise AssertionError(cmd)

        mock_co.side_effect = _side_effect
        with pytest.raises(EXP009Error, match="dirty"):
            require_clean_source_tree()
        with pytest.raises(EXP009Error, match="dirty"):
            ensure_model_paper_approved(
                MagicMock(),
                effective_time=HOLDOUT_START,
                code_commit=_VALID_CODE_COMMIT,
            )


def test_require_signed_dataset_ids_rejects_overrides() -> None:
    with pytest.raises(EXP009Error, match="DATA-011"):
        require_signed_dataset_ids(bar_panel_dataset_id="ds_other")
    with pytest.raises(EXP009Error, match="UNIVERSE-006"):
        require_signed_dataset_ids(universe_dataset_id="ds_other")
    require_signed_dataset_ids(
        bar_panel_dataset_id=BAR_PANEL_DATASET_ID,
        universe_dataset_id=UNIVERSE_DATASET_ID,
    )


def test_code_commit_must_match_executing_source() -> None:
    def _side_effect(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["git", "rev-parse"]:
            return _VALID_CODE_COMMIT + "\n"
        if cmd[:2] == ["git", "status"]:
            return ""
        raise AssertionError(cmd)

    with patch(
        "cryptofactors.experiments.exp009.subprocess.check_output",
        side_effect=_side_effect,
    ):
        head = get_executing_source_commit()
        assert head == _VALID_CODE_COMMIT
        registry = MagicMock()
        registry.get_current_state.return_value = None
        ensure_model_paper_approved(
            registry,
            effective_time=HOLDOUT_START,
            code_commit=head,
        )
        assert registry.register_candidate.called
        fake = "a" * 40
        assert fake != head
        with pytest.raises(EXP009Error, match="executing source"):
            ensure_model_paper_approved(
                MagicMock(),
                effective_time=HOLDOUT_START,
                code_commit=fake,
            )


def test_run_holdout_raises_when_sealed() -> None:
    runner = _stub_runner()
    # No coverage → sealed; must not call into the paper loop.
    with pytest.raises(EXP009HoldoutNotReadyError):
        runner.run_holdout(now=_POST_HOLDOUT_NOW)


def test_run_holdout_raises_on_future_bar_claim() -> None:
    runner = _stub_runner()
    with pytest.raises(EXP009Error, match="wall clock"):
        runner.run_holdout(
            latest_available_bar=HOLDOUT_END,
            now=DATA_LOCK_DATE,
        )


def test_ensure_model_paper_approved_rejects_placeholder_commit() -> None:
    registry = MagicMock()
    registry.get_current_state.return_value = None
    with pytest.raises(EXP009Error, match="repository SHA|placeholder|hexadecimal|length"):
        ensure_model_paper_approved(
            registry,
            effective_time=HOLDOUT_START,
            code_commit="EXP-009",
        )


def test_code_commit_rejects_non_hex() -> None:
    # Length-valid (>=7) but not hexadecimal — must hit the hex check, not length.
    bad = "nothex1"
    assert 7 <= len(bad) <= 40
    registry = MagicMock()
    with pytest.raises(EXP009Error, match="hexadecimal"):
        ensure_model_paper_approved(
            registry,
            effective_time=HOLDOUT_START,
            code_commit=bad,
        )
    binding = MagicMock()
    binding.universe_dataset_id = UNIVERSE_DATASET_ID
    binding.bar_panel_dataset_id = BAR_PANEL_DATASET_ID
    with pytest.raises(EXP009Error, match="hexadecimal"):
        EXP009Runner(
            universe_binding=binding,
            promotion_registry=MagicMock(),
            as_of_store=MagicMock(),
            get_prices_at=lambda dt, univ: {},
            code_commit=bad,
        )


def test_ensure_model_paper_approved_registers_with_real_sha() -> None:
    registry = MagicMock()
    # Walk RESEARCH_CANDIDATE → RESEARCH_ACCEPTED → PAPER_APPROVED.
    registry.get_current_state.return_value = None

    def _transition(payload: Any, target_state: Any, reason: str = "") -> None:
        return None

    registry.transition_state.side_effect = _transition

    def _side_effect(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["git", "rev-parse"]:
            return _VALID_CODE_COMMIT + "\n"
        if cmd[:2] == ["git", "status"]:
            return ""
        raise AssertionError(cmd)

    with patch(
        "cryptofactors.experiments.exp009.subprocess.check_output",
        side_effect=_side_effect,
    ):
        ensure_model_paper_approved(
            registry,
            effective_time=HOLDOUT_START,
            code_commit=_VALID_CODE_COMMIT,
        )
    assert registry.register_candidate.called
    # First payload must carry the real SHA, not a ticket id.
    first_payload = registry.register_candidate.call_args[0][0]
    assert first_payload.code_commit == _VALID_CODE_COMMIT
    assert first_payload.experiment_fingerprint == _PINNED_FINGERPRINT
    assert first_payload.dataset_ids == (BAR_PANEL_DATASET_ID, UNIVERSE_DATASET_ID)


def test_run_exploratory_rejects_times_into_holdout() -> None:
    runner = _stub_runner()
    # HOLDOUT_START is itself a Friday, so exploration_decision_times returns
    # the holdout calendar and the bleed guard must fire.
    with pytest.raises(EXP009Error, match="strictly before holdout start"):
        runner.run_exploratory(
            start=HOLDOUT_START,
            end=HOLDOUT_END,
        )


def test_run_exploratory_bleed_guard_pre_holdout_start_past_lock_end() -> None:
    """Pre-holdout Friday start with end past lock: bleed guard, not empty window."""
    runner = _stub_runner()
    with pytest.raises(EXP009Error, match="strictly before holdout start"):
        runner.run_exploratory(
            start=datetime(2026, 7, 24, tzinfo=UTC),
            end=HOLDOUT_END,
        )


# ---------------------------------------------------------------------------
# End-to-end synthetic protocol (in-memory, no market data)
# ---------------------------------------------------------------------------


def test_synthetic_protocol_cannot_open_holdout_without_coverage() -> None:
    rng = np.random.default_rng(20260727)
    weekly = list(rng.normal(0.002, 0.03, size=26))
    total = float(np.prod(1.0 + np.asarray(weekly)) - 1.0)
    bootstrap = stationary_bootstrap_mean_pvalue(weekly, n_resamples=400, seed=20260727)
    decision = apply_decision_rule(total, float(bootstrap["p_value"]))
    readiness = assess_holdout_readiness(now=_POST_HOLDOUT_NOW)

    assert readiness.ready is False
    with pytest.raises(EXP009HoldoutNotReadyError):
        require_holdout_ready(readiness)

    artifact = build_artifact(
        mode=EXP009Mode.SYNTHETIC,
        universe_binding=None,
        readiness=readiness,
        bootstrap=bootstrap,
        decision_rule=decision,
        verdict=HypothesisVerdict.EXPLORATORY_ONLY,
        extra={
            "synthetic": {
                "total_net_return": total,
                "weekly_net_returns": weekly,
            },
            "note": "synthetic only",
        },
    )
    assert artifact["verdict"] == HypothesisVerdict.EXPLORATORY_ONLY.value
    assert artifact["holdout"]["ready"] is False
    assert artifact["survivorship_invalid"] is False
    assert artifact["universe_dataset_id"] == UNIVERSE_DATASET_ID
    assert artifact["bar_panel_dataset_id"] == BAR_PANEL_DATASET_ID
    assert decision["verdict"] in {
        HypothesisVerdict.ACCEPT.value,
        HypothesisVerdict.REJECT.value,
    }
    assert artifact["verdict"] != HypothesisVerdict.ACCEPT.value


def test_hypothesis_verdict_and_mode_enums() -> None:
    assert EXP009Mode.READINESS.value == "readiness"
    assert EXP009Mode.EXPLORATORY.value == "exploratory"
    assert EXP009Mode.HOLDOUT.value == "holdout"
    assert EXP009Mode.SYNTHETIC.value == "synthetic"
    assert HypothesisVerdict.SEALED.value == "SEALED"
    assert HypothesisVerdict.EXPLORATORY_ONLY.value == "EXPLORATORY_ONLY"
