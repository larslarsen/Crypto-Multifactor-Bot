"""Execution domain module (EXEC-001, EXEC-002)."""

from cryptofactors.execution.errors import (
    DrawdownLimitExceededError,
    KillSwitchActiveError,
    LiveExecutionError,
    PaperExecutionError,
    PaperOpsError,
    RiskLimitViolationError,
    UnapprovedArtifactError,
)
from cryptofactors.execution.live import (
    MAX_GROSS_LEVERAGE,
    MAX_SINGLE_ASSET_WEIGHT,
    LiveBroker,
    PreTradeRiskValidator,
    VenueAdapter,
    load_credentials_from_env,
    new_live_order,
)
from cryptofactors.execution.models import (
    FlattenSignal,
    LiveOrder,
    LiveOrderState,
    LiveOrderStatus,
    PaperAccountState,
    PaperOpsStatus,
    PaperOrder,
    PaperTrade,
)
from cryptofactors.execution.paper import PaperBroker
from cryptofactors.execution.paper_harden import (
    PaperHardenReport,
    build_harden_report,
    write_harden_report_artifact,
)
from cryptofactors.execution.paper_loop import (
    FactorDrivenPaperLoop,
    PaperLoopPeriodLog,
    PaperLoopResult,
)
from cryptofactors.execution.paper_monitor import PaperOpsMonitor
from cryptofactors.execution.paper_store import PaperSessionStore
from cryptofactors.execution.venue_probe import ReadOnlyVenueProbeAdapter

__all__ = [
    "DrawdownLimitExceededError",
    "FactorDrivenPaperLoop",
    "FlattenSignal",
    "KillSwitchActiveError",
    "LiveBroker",
    "LiveExecutionError",
    "LiveOrder",
    "LiveOrderState",
    "LiveOrderStatus",
    "MAX_GROSS_LEVERAGE",
    "MAX_SINGLE_ASSET_WEIGHT",
    "PaperAccountState",
    "PaperBroker",
    "PaperExecutionError",
    "PaperHardenReport",
    "PaperLoopPeriodLog",
    "PaperLoopResult",
    "PaperOpsError",
    "PaperOpsMonitor",
    "PaperOpsStatus",
    "PaperOrder",
    "PaperSessionStore",
    "PaperTrade",
    "PreTradeRiskValidator",
    "ReadOnlyVenueProbeAdapter",
    "RiskLimitViolationError",
    "UnapprovedArtifactError",
    "VenueAdapter",
    "build_harden_report",
    "load_credentials_from_env",
    "new_live_order",
    "write_harden_report_artifact",
]
