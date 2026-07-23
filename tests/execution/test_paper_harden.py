"""Tests for HARDEN-001 Paper Path Hardening, Read-Only Venue Probe, and Verification Report."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cryptofactors.execution import (
    LiveExecutionError,
    LiveOrder,
    PaperExecutionError,
    PaperOpsStatus,
    ReadOnlyVenueProbeAdapter,
    build_harden_report,
    write_harden_report_artifact,
)

UTC = timezone.utc


def test_venue_probe_adapter_ping_and_order_guards() -> None:
    """HARDEN-001: ReadOnlyVenueProbeAdapter allows ping but strictly blocks all order methods."""
    adapter = ReadOnlyVenueProbeAdapter(venue_name="stub_test")

    # Order submission must raise LiveExecutionError
    dummy_order = LiveOrder(
        order_id="ord_01",
        symbol="BTCUSD",
        side="BUY",
        quantity=1.0,
    )
    with pytest.raises(LiveExecutionError, match="Order submission is disabled"):
        adapter.submit_order(dummy_order, {"api_key": "k"})

    with pytest.raises(LiveExecutionError, match="Order cancellation is disabled"):
        adapter.cancel_order("ven_01", {"api_key": "k"})

    with pytest.raises(LiveExecutionError, match="Order status queries are disabled"):
        adapter.get_order_status("ven_01", {"api_key": "k"})


def test_harden_report_structure_and_live_eligibility() -> None:
    """HARDEN-001: PaperHardenReport must enforce live_eligible=False and capture probe results."""
    t0 = datetime.now(UTC)
    ops_status = PaperOpsStatus(
        model_artifact_id="mod_tsmom_30_7_v1",
        promotion_state="PAPER_APPROVED",
        gate_status="OK",
        last_rebalance_time=t0,
        last_equity=104894.79,
        initial_cash=100000.0,
        total_net_return=0.048948,
        peak_equity=104894.79,
        current_drawdown=0.0,
        open_positions_count=10,
        total_trades_count=80,
        paper_observation_reference="obs_12345",
        drawdown_alert_triggered=False,
    )

    probe_res = {
        "status": "PING_OK",
        "venue": "binance_spot_public",
        "latency_ms": 15.2,
    }

    report = build_harden_report(
        ops_status,
        data_mode="synthetic",
        venue_probe_result=probe_res,
    )

    assert report.model_artifact_id == "mod_tsmom_30_7_v1"
    assert report.data_mode == "synthetic"
    assert report.gate_status == "OK"
    assert report.live_eligible is False  # ALWAYS False per HARDEN-001
    assert report.venue_probe_result == probe_res

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "harden_report.json"
        written = write_harden_report_artifact(report, out_path)
        assert written.exists()
