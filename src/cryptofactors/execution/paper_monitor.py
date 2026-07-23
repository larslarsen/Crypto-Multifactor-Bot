"""PAPER-003 — Paper Ops Health & Status Monitor.

Generates structured health/status report artifacts for PAPER_APPROVED model artifacts,
summarizing promotion gate status, equity curve, drawdown, open positions, and observation references.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptofactors.execution.models import PaperOpsStatus
from cryptofactors.execution.paper import PaperBroker
from cryptofactors.promotion import PromotionError, PromotionRegistry, PromotionTarget

UTC = timezone.utc
DEFAULT_OPS_STATUS_PATH = Path("research/sprint_004/09_PAPER_OPS_STATUS.json")


class PaperOpsMonitor:
    """Operations health and monitoring inspector for paper trading sessions."""

    def __init__(
        self,
        promotion_registry: PromotionRegistry,
    ) -> None:
        self.promotion_registry: PromotionRegistry = promotion_registry

    def inspect_session(
        self,
        model_artifact_id: str,
        broker: PaperBroker | None = None,
        *,
        paper_observation_reference: str | None = None,
        drawdown_alert_triggered: bool = False,
    ) -> PaperOpsStatus:
        """Inspect paper session state and produce a PaperOpsStatus report."""
        # 1. Gate check
        current_state = self.promotion_registry.get_current_state(model_artifact_id)
        state_str = current_state.value if current_state else "UNREGISTERED"

        gate_status = "FAIL"
        try:
            event = self.promotion_registry.get_active_promoted_artifact(
                model_artifact_id, PromotionTarget.PAPER
            )
            if event and event.promotion_state.value == "PAPER_APPROVED":
                gate_status = "OK"
        except PromotionError:
            gate_status = "FAIL"

        # 2. Broker state metrics
        last_rebalance_time: datetime | None = None
        last_equity = 100_000.0
        initial_cash = 100_000.0
        peak_equity = 100_000.0
        open_pos_count = 0
        total_trades = 0

        if broker is not None:
            trades = broker.get_trade_history()
            total_trades = len(trades)
            if trades:
                last_rebalance_time = trades[-1].timestamp

            positions = broker.get_positions()
            open_pos_count = len(positions)
            last_equity = broker.get_cash()  # Base unallocated cash or mark-to-market
            initial_cash = 100_000.0

        net_return = (last_equity - initial_cash) / initial_cash
        drawdown = max(0.0, (peak_equity - last_equity) / peak_equity) if peak_equity > 0 else 0.0

        return PaperOpsStatus(
            model_artifact_id=model_artifact_id,
            promotion_state=state_str,
            gate_status=gate_status,
            last_rebalance_time=last_rebalance_time,
            last_equity=round(last_equity, 2),
            initial_cash=round(initial_cash, 2),
            total_net_return=round(net_return, 6),
            peak_equity=round(peak_equity, 2),
            current_drawdown=round(drawdown, 6),
            open_positions_count=open_pos_count,
            total_trades_count=total_trades,
            paper_observation_reference=paper_observation_reference,
            drawdown_alert_triggered=drawdown_alert_triggered,
            report_generated_at=datetime.now(UTC),
        )

    def write_status_artifact(
        self,
        status: PaperOpsStatus,
        output_path: Path | str = DEFAULT_OPS_STATUS_PATH,
    ) -> Path:
        """Serialize PaperOpsStatus report to JSON artifact."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {
            "model_artifact_id": status.model_artifact_id,
            "promotion_state": status.promotion_state,
            "gate_status": status.gate_status,
            "last_rebalance_time": status.last_rebalance_time.isoformat() if status.last_rebalance_time else None,
            "last_equity": status.last_equity,
            "initial_cash": status.initial_cash,
            "total_net_return": status.total_net_return,
            "peak_equity": status.peak_equity,
            "current_drawdown": status.current_drawdown,
            "open_positions_count": status.open_positions_count,
            "total_trades_count": status.total_trades_count,
            "paper_observation_reference": status.paper_observation_reference,
            "drawdown_alert_triggered": status.drawdown_alert_triggered,
            "report_generated_at": status.report_generated_at.isoformat(),
        }

        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return p
