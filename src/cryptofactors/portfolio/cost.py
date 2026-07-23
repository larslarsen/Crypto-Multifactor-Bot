import dataclasses
from decimal import Decimal

@dataclasses.dataclass(frozen=True, slots=True)
class CostConfig:
    """Cost model for portfolio simulation."""
    fee_bps: Decimal
    slippage_bps: Decimal
    cost_version: str
