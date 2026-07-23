"""Tests for EXEC-002 Live Execution Routing and LiveBroker."""

import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cryptofactors.execution import (
    KillSwitchActiveError,
    LiveBroker,
    LiveOrder,
    LiveOrderState,
    LiveOrderStatus,
    PreTradeRiskValidator,
    RiskLimitViolationError,
    UnapprovedArtifactError,
    new_live_order,
)
from cryptofactors.promotion import (
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)


class StubVenue:
    """In-memory venue adapter recording calls (no real HTTP)."""

    def __init__(self) -> None:
        self.submit_calls: list[tuple[LiveOrder, dict[str, str]]] = []
        self.cancel_calls: list[tuple[str, dict[str, str]]] = []
        self.status_calls: list[tuple[str, dict[str, str]]] = []
        self._next_id = 1

    def submit_order(self, order: LiveOrder, credentials: Mapping[str, str]) -> str:
        self.submit_calls.append((order, dict(credentials)))
        vid = f"ven_{self._next_id:04d}"
        self._next_id += 1
        return vid

    def cancel_order(self, venue_order_id: str, credentials: Mapping[str, str]) -> bool:
        self.cancel_calls.append((venue_order_id, dict(credentials)))
        return True

    def get_order_status(self, venue_order_id: str, credentials: Mapping[str, str]) -> LiveOrderStatus:
        self.status_calls.append((venue_order_id, dict(credentials)))
        return LiveOrderStatus(
            order_id=venue_order_id,
            venue_order_id=venue_order_id,
            state=LiveOrderState.FILLED,
            filled_quantity=1.0,
            avg_fill_price=50_000.0,
            timestamp=datetime.now(timezone.utc),
        )


def live_approved_payload(
    model_artifact_id: str = "art_live_v1",
) -> PromotionIdentityPayload:
    return PromotionIdentityPayload(
        model_artifact_id=model_artifact_id,
        experiment_fingerprint="fp_live",
        dataset_ids=("ds_1h",),
        universe_ids=("cmc_univ",),
        code_commit="commit_live",
        config_version="cfg1",
        feature_version="feat1",
        representation_version="rep1",
        portfolio_version="port1",
        cost_model_version="cost1",
        risk_policy_version="risk1",
        target_stage=PromotionTarget.LIVE,
        effective_time=datetime.now(timezone.utc),
        approving_authority="Owner authorization board",
        evidence_reference="rev_001",
        paper_observation_reference="holdout_14day_passed",
    )


def promote_to_live(registry: PromotionRegistry, model_artifact_id: str = "art_live_v1") -> None:
    cand = PromotionIdentityPayload(
        model_artifact_id=model_artifact_id,
        experiment_fingerprint="fp_live",
        dataset_ids=("ds_1h",),
        universe_ids=("cmc_univ",),
        code_commit="commit_live",
        config_version="cfg1",
        feature_version="feat1",
        representation_version="rep1",
        portfolio_version="port1",
        cost_model_version="cost1",
        risk_policy_version="risk1",
        target_stage=PromotionTarget.RESEARCH,
        effective_time=datetime.now(timezone.utc),
        approving_authority="Owner",
        evidence_reference="rev_001",
    )
    registry.register_candidate(cand)

    paper = PromotionIdentityPayload(
        model_artifact_id=model_artifact_id,
        experiment_fingerprint="fp_live",
        dataset_ids=("ds_1h",),
        universe_ids=("cmc_univ",),
        code_commit="commit_live",
        config_version="cfg1",
        feature_version="feat1",
        representation_version="rep1",
        portfolio_version="port1",
        cost_model_version="cost1",
        risk_policy_version="risk1",
        target_stage=PromotionTarget.PAPER,
        effective_time=datetime.now(timezone.utc),
        approving_authority="Lead Quant",
        evidence_reference="rev_001",
    )
    registry.transition_state(paper, PromotionState.PAPER_APPROVED, reason="paper ok")

    live = live_approved_payload(model_artifact_id)
    registry.transition_state(live, PromotionState.LIVE_APPROVED, reason="live ok")


class TestUnapprovedArtifactFailsBeforeHTTP:
    """Acceptance item #5: unapproved / non-LIVE_APPROVED artifact -> hard error before HTTP call."""

    def test_unregistered_artifact_fails_before_http(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "control.db"
            registry = PromotionRegistry(db_path)
            venue = StubVenue()

            with pytest.raises(UnapprovedArtifactError, match="failed live promotion gate"):
                LiveBroker(
                    "never_registered",
                    registry,
                    venue,
                    credentials={"api_key": "k", "api_secret": "s"},
                    load_credentials=False,
                )

            assert venue.submit_calls == []
            assert venue.cancel_calls == []
            assert venue.status_calls == []

    def test_paper_approved_artifact_fails_before_http(self) -> None:
        """An artifact only at PAPER_APPROVED must not be routable live."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "control.db"
            registry = PromotionRegistry(db_path)
            venue = StubVenue()

            cand = PromotionIdentityPayload(
                model_artifact_id="art_paper_only",
                experiment_fingerprint="fp",
                dataset_ids=("ds",),
                universe_ids=("u",),
                code_commit="c",
                config_version="cfg",
                feature_version="f",
                representation_version="r",
                portfolio_version="p",
                cost_model_version="cm",
                risk_policy_version="rp",
                target_stage=PromotionTarget.RESEARCH,
                effective_time=datetime.now(timezone.utc),
                approving_authority="Owner",
                evidence_reference="rev",
            )
            registry.register_candidate(cand)
            paper_payload = PromotionIdentityPayload(
                model_artifact_id="art_paper_only",
                experiment_fingerprint="fp",
                dataset_ids=("ds",),
                universe_ids=("u",),
                code_commit="c",
                config_version="cfg",
                feature_version="f",
                representation_version="r",
                portfolio_version="p",
                cost_model_version="cm",
                risk_policy_version="rp",
                target_stage=PromotionTarget.PAPER,
                effective_time=datetime.now(timezone.utc),
                approving_authority="Lead Quant",
                evidence_reference="rev",
            )
            registry.transition_state(paper_payload, PromotionState.PAPER_APPROVED, reason="paper")

            with pytest.raises(UnapprovedArtifactError, match="failed live promotion gate"):
                LiveBroker(
                    "art_paper_only",
                    registry,
                    venue,
                    credentials={"api_key": "k", "api_secret": "s"},
                    load_credentials=False,
                )

            assert venue.submit_calls == []


class TestPreTradeRiskLimits:
    """Acceptance item #6: leverage > 1.0 or single-asset weight > 0.15 -> rejected pre-trade."""

    def test_leverage_over_one_rejected(self) -> None:
        validator = PreTradeRiskValidator()
        weights = {"BTC": 0.6, "ETH": 0.6}  # 1.2 gross
        with pytest.raises(RiskLimitViolationError, match="Gross leverage"):
            validator.validate(weights)

    def test_single_asset_over_cap_rejected(self) -> None:
        validator = PreTradeRiskValidator()
        weights = {"BTC": 0.5}  # 0.5 > 0.15
        with pytest.raises(RiskLimitViolationError, match="Single-asset weight"):
            validator.validate(weights)

    def test_valid_weights_pass(self) -> None:
        validator = PreTradeRiskValidator()
        weights = {"BTC": 0.10, "ETH": 0.10, "SOL": 0.05}
        validator.validate(weights)  # no raise

    def test_live_broker_rejects_risky_order_before_http(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "control.db"
            registry = PromotionRegistry(db_path)
            promote_to_live(registry, "art_live_v1")
            venue = StubVenue()

            broker = LiveBroker(
                "art_live_v1",
                registry,
                venue,
                credentials={"api_key": "k", "api_secret": "s"},
                load_credentials=False,
            )
            order = new_live_order("BTC", "BUY", 0.1)
            risky_weights = {"BTC": 0.5}  # over single-asset cap

            with pytest.raises(RiskLimitViolationError, match="Single-asset weight"):
                broker.submit_order(order, risky_weights)

            assert venue.submit_calls == []


class TestMockedHTTPOnly:
    """Acceptance item #7: mocked HTTP only (no live network in unit tests)."""

    def test_submit_order_uses_venue_adapter_not_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "control.db"
            registry = PromotionRegistry(db_path)
            promote_to_live(registry, "art_live_v1")
            venue = StubVenue()

            broker = LiveBroker(
                "art_live_v1",
                registry,
                venue,
                credentials={"api_key": "k", "api_secret": "s"},
                load_credentials=False,
            )

            order = new_live_order("BTC", "BUY", 0.1)
            weights = {"BTC": 0.10}
            status = broker.submit_order(order, weights)

            assert status.state == LiveOrderState.SUBMITTED
            assert venue.submit_calls != []
            assert len(venue.submit_calls) == 1
            submitted_order, creds = venue.submit_calls[0]
            assert submitted_order.order_id == order.order_id


class TestKillSwitch:
    """Kill-switch: refuses new orders and surfaces flatten signal."""

    def test_kill_switch_refuses_new_orders(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "control.db"
            registry = PromotionRegistry(db_path)
            promote_to_live(registry, "art_live_v1")
            venue = StubVenue()

            broker = LiveBroker(
                "art_live_v1",
                registry,
                venue,
                credentials={"api_key": "k", "api_secret": "s"},
                load_credentials=False,
            )
            signal = broker.activate_kill_switch(reason="manual")

            assert broker.is_kill_switch_active() is True
            assert signal.reason == "manual"

            order = new_live_order("BTC", "BUY", 0.1)
            with pytest.raises(KillSwitchActiveError, match="Kill-switch active"):
                broker.submit_order(order, {"BTC": 0.10})

    def test_registry_revocation_activates_kill_switch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "control.db"
            registry = PromotionRegistry(db_path)
            promote_to_live(registry, "art_live_v1")
            venue = StubVenue()

            broker = LiveBroker(
                "art_live_v1",
                registry,
                venue,
                credentials={"api_key": "k", "api_secret": "s"},
                load_credentials=False,
            )

            # Suspend the live artifact (append-only transition out of LIVE_APPROVED)
            live_suspended = PromotionIdentityPayload(
                model_artifact_id="art_live_v1",
                experiment_fingerprint="fp_live",
                dataset_ids=("ds_1h",),
                universe_ids=("cmc_univ",),
                code_commit="commit_live",
                config_version="cfg1",
                feature_version="feat1",
                representation_version="rep1",
                portfolio_version="port1",
                cost_model_version="cost1",
                risk_policy_version="risk1",
                target_stage=PromotionTarget.LIVE,
                effective_time=datetime.now(timezone.utc),
                approving_authority="Owner authorization board",
                evidence_reference="rev_001",
                paper_observation_reference="holdout_14day_passed",
            )
            registry.transition_state(live_suspended, PromotionState.LIVE_SUSPENDED, reason="revoked")

            activated = broker.check_registry_and_kill_if_revoked()
            assert activated is True
            assert broker.is_kill_switch_active() is True