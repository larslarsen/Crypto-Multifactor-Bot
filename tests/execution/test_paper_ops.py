"""Tests for PAPER-003 & PAPER-004 Paper Ops Monitoring, Persistence, and State Resume."""

import tempfile
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cryptofactors.execution import (
    FactorDrivenPaperLoop,
    PaperAccountState,
    PaperBroker,
    PaperOpsMonitor,
    PaperOpsStatus,
    PaperSessionStore,
    PaperTrade,
)
from cryptofactors.factors.tsmom import TimeSeriesMomentumFactor
from cryptofactors.promotion import (
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)

UTC = timezone.utc
MODEL_ARTIFACT_ID = "mod_tsmom_30_7_v1"
FINGERPRINT = "87469a44a18449bee23de76b1312413fd3e5a649a6677e3509a8c270caea3318"


def test_session_store_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        store = PaperSessionStore(db_path)

        t0 = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
        state = PaperAccountState(
            cash=95_000.0,
            positions={"BTC": 1.0, "ETH": 10.0},
            equity=105_000.0,
            timestamp=t0,
        )

        snap_id = store.save_snapshot("mod_v1", state, {"BTC": 0.5, "ETH": 0.5})
        assert snap_id.startswith("snap_")

        trade = PaperTrade(
            trade_id="tr_001",
            symbol="BTC",
            side="BUY",
            quantity=1.0,
            base_price=50_000.0,
            effective_price=50_025.0,
            fee=25.0,
            notional=50_025.0,
            timestamp=t0,
        )
        store.save_trades("mod_v1", [trade])

        loaded_state = store.load_latest_snapshot("mod_v1")
        assert loaded_state is not None
        assert loaded_state.cash == 95_000.0
        assert loaded_state.equity == 105_000.0
        assert loaded_state.positions == {"BTC": 1.0, "ETH": 10.0}

        loaded_trades = store.load_trade_history("mod_v1")
        assert len(loaded_trades) == 1
        assert loaded_trades[0].trade_id == "tr_001"
        assert loaded_trades[0].symbol == "BTC"


def test_broker_restore_from_store() -> None:
    """PAPER-004: Verify PaperBroker restores cash balance, open positions, and trade history from store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        # Register and promote to PAPER_APPROVED
        cand = PromotionIdentityPayload(
            model_artifact_id="mod_restore_test",
            experiment_fingerprint=FINGERPRINT,
            dataset_ids=("ds1",),
            universe_ids=("u1",),
            code_commit="c1",
            config_version="cfg1",
            feature_version="f1",
            representation_version="r1",
            portfolio_version="p1",
            cost_model_version="cm1",
            risk_policy_version="rp1",
            target_stage=PromotionTarget.RESEARCH,
            effective_time=datetime.now(UTC),
            approving_authority="Lead Quant",
            evidence_reference="rev1",
        )
        registry.register_candidate(cand)

        paper = PromotionIdentityPayload(
            model_artifact_id="mod_restore_test",
            experiment_fingerprint=FINGERPRINT,
            dataset_ids=("ds1",),
            universe_ids=("u1",),
            code_commit="c1",
            config_version="cfg1",
            feature_version="f1",
            representation_version="r1",
            portfolio_version="p1",
            cost_model_version="cost1",
            risk_policy_version="risk1",
            target_stage=PromotionTarget.PAPER,
            effective_time=datetime.now(UTC),
            approving_authority="Lead Quant",
            evidence_reference="rev2",
        )
        registry.transition_state(paper, PromotionState.PAPER_APPROVED, reason="paper ok")

        store = PaperSessionStore(db_path)
        t0 = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
        state = PaperAccountState(
            cash=50_000.0,
            positions={"BTC": 1.0},
            equity=100_000.0,
            timestamp=t0,
        )
        store.save_snapshot("mod_restore_test", state, {"BTC": 0.5})

        trade = PaperTrade(
            trade_id="tr_res_01",
            symbol="BTC",
            side="BUY",
            quantity=1.0,
            base_price=50_000.0,
            effective_price=50_025.0,
            fee=25.0,
            notional=50_025.0,
            timestamp=t0,
        )
        store.save_trades("mod_restore_test", [trade])

        # Instantiate fresh broker and restore from store
        broker = PaperBroker("mod_restore_test", registry, initial_cash=100_000.0)
        restored = broker.restore_from_store(store, "mod_restore_test")

        assert restored is True
        assert broker.get_cash() == 50_000.0
        assert broker.get_positions() == {"BTC": 1.0}
        assert len(broker.get_trade_history()) == 1


def test_ops_monitor_uses_mark_to_market_equity() -> None:
    """PAPER-004: Verify PaperOpsMonitor uses MTM equity when current_prices are supplied."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        cand = PromotionIdentityPayload(
            model_artifact_id=MODEL_ARTIFACT_ID,
            experiment_fingerprint=FINGERPRINT,
            dataset_ids=("ds1",),
            universe_ids=("u1",),
            code_commit="c1",
            config_version="cfg1",
            feature_version="f1",
            representation_version="r1",
            portfolio_version="p1",
            cost_model_version="cm1",
            risk_policy_version="rp1",
            target_stage=PromotionTarget.RESEARCH,
            effective_time=datetime.now(UTC),
            approving_authority="Lead Quant",
            evidence_reference="rev1",
        )
        registry.register_candidate(cand)

        paper = PromotionIdentityPayload(
            model_artifact_id=MODEL_ARTIFACT_ID,
            experiment_fingerprint=FINGERPRINT,
            dataset_ids=("ds1",),
            universe_ids=("u1",),
            code_commit="c1",
            config_version="cfg1",
            feature_version="f1",
            representation_version="r1",
            portfolio_version="p1",
            cost_model_version="cost1",
            risk_policy_version="risk1",
            target_stage=PromotionTarget.PAPER,
            effective_time=datetime.now(UTC),
            approving_authority="Lead Quant",
            evidence_reference="rev2",
        )
        registry.transition_state(paper, PromotionState.PAPER_APPROVED, reason="paper ok")

        broker = PaperBroker(MODEL_ARTIFACT_ID, registry, initial_cash=100_000.0)
        prices = {"BTC": 50_000.0}
        t0 = datetime(2026, 7, 23, tzinfo=UTC)

        # Rebalance: 50% BTC -> cash 49,973.75, pos 1.0 BTC
        broker.rebalance({"BTC": 0.5}, prices, t0)

        monitor = PaperOpsMonitor(registry)

        # Without prices -> returns unallocated cash (~49973)
        status_cash = monitor.inspect_session(MODEL_ARTIFACT_ID, broker=broker)
        assert status_cash.last_equity == pytest.approx(49949.99, abs=1.0)

        # With current_prices -> returns mark-to-market total equity (~100000)
        status_mtm = monitor.inspect_session(MODEL_ARTIFACT_ID, broker=broker, current_prices=prices)
        assert status_mtm.last_equity == pytest.approx(99949.99, abs=1.0)


def test_drawdown_alert_callback_triggers() -> None:
    alerts: list[tuple[str, float, float]] = []

    def on_alert(model_id: str, dd: float, eq: float) -> None:
        alerts.append((model_id, dd, eq))

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        registry = PromotionRegistry(db_path)

        cand = PromotionIdentityPayload(
            model_artifact_id="mod_dd_test",
            experiment_fingerprint="fp1",
            dataset_ids=("ds1",),
            universe_ids=("u1",),
            code_commit="c1",
            config_version="cfg1",
            feature_version="f1",
            representation_version="r1",
            portfolio_version="p1",
            cost_model_version="cm1",
            risk_policy_version="rp1",
            target_stage=PromotionTarget.RESEARCH,
            effective_time=datetime.now(UTC),
            approving_authority="Lead Quant",
            evidence_reference="rev1",
        )
        registry.register_candidate(cand)

        paper = PromotionIdentityPayload(
            model_artifact_id="mod_dd_test",
            experiment_fingerprint="fp1",
            dataset_ids=("ds1",),
            universe_ids=("u1",),
            code_commit="c1",
            config_version="cfg1",
            feature_version="f1",
            representation_version="r1",
            portfolio_version="p1",
            cost_model_version="cost1",
            risk_policy_version="risk1",
            target_stage=PromotionTarget.PAPER,
            effective_time=datetime.now(UTC) - timedelta(days=20),
            approving_authority="Lead Quant",
            evidence_reference="rev2",
        )
        registry.transition_state(paper, PromotionState.PAPER_APPROVED, reason="paper ok")

        # Mock price store where factor returns positive score (long BTC at 50k), then price drops to 30k on May 2
        class MockDroppingStore:
            def latest_available(self, dataset_id: str, keys: list[object], fields: list[str], decision_time: datetime, max_age: object = None) -> object:
                import pyarrow as pa
                if "ref_instrument" in dataset_id:
                    return pa.table({"instrument_id": pa.array(["BTC"], pa.string())})

                # For tsmom: at t-7d return 50000.0, at t-30d return 40000.0 -> positive score
                p_val = 50000.0 if decision_time >= datetime(2026, 3, 20, tzinfo=UTC) else 40000.0
                return pa.table({
                    "instrument_id": pa.array(["BTC"], pa.string()),
                    "close": pa.array([p_val], pa.float64()),
                    "availability_time": pa.array([int(decision_time.timestamp() * 1e6)], pa.int64()),
                    "period_start": pa.array([int(decision_time.timestamp() * 1e6)], pa.int64()),
                })

            def get_prices_at(self, dt: datetime, universe: Sequence[str]) -> dict[str, float]:
                if dt < datetime(2026, 5, 1, tzinfo=UTC):
                    return {"BTC": 50000.0}
                return {"BTC": 10000.0}

        store = MockDroppingStore()
        factor = TimeSeriesMomentumFactor(store, lookback_days=30, skip_days=7, market_dataset_id="ds1")

        loop = FactorDrivenPaperLoop(
            model_artifact_id="mod_dd_test",
            promotion_registry=registry,
            factor=factor,
            initial_cash=100_000.0,
            max_drawdown_threshold=0.10,
            alert_callback=on_alert,
        )

        decision_times = [
            datetime(2026, 4, 1, tzinfo=UTC),
            datetime(2026, 4, 15, tzinfo=UTC),
            datetime(2026, 5, 2, tzinfo=UTC),  # price drops here
        ]

        res = loop.run_loop(
            universe=["BTC"],
            decision_times=decision_times,
            get_prices_at=store.get_prices_at,
        )

        assert res.drawdown_alert_triggered is True
        assert len(alerts) > 0
        assert alerts[0][0] == "mod_dd_test"
