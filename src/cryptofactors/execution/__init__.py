"""Execution domain module (EXEC-001, EXEC-002)."""

from cryptofactors.execution.errors import (
    KillSwitchActiveError,
    LiveExecutionError,
    PaperExecutionError,
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
    PaperOrder,
    PaperTrade,
)
from cryptofactors.execution.paper import PaperBroker

__all__ = [
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
    "PaperOrder",
    "PaperTrade",
    "PreTradeRiskValidator",
    "RiskLimitViolationError",
    "UnapprovedArtifactError",
    "VenueAdapter",
    "load_credentials_from_env",
    "new_live_order",
]
