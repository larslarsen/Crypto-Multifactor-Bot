"""EXEC-003 — Paper allocation risk enforcement (PAPER-006).

Provides a deterministic clip-and-renormalize enforcer that maps any raw target
weights into a risk-compliant set before they reach ``PaperBroker.rebalance``.

Policy (per PAPER-006 / AUD-006):
1. Clip each single-asset weight to ``[-max_single_weight, max_single_weight]``.
2. If gross leverage exceeds ``max_gross_leverage``, scale all weights down
   uniformly so that gross leverage equals the limit.
3. Drop zero/rounded-to-zero weights from the returned dict.

This is *enforcement* (clip+renormalize), not validation. The live path uses
``PreTradeRiskValidator`` which rejects orders; the paper path must stay running
while recording the actual risk-compliant weights used.
"""

from __future__ import annotations

from collections.abc import Mapping

from cryptofactors.execution.live import (
    MAX_GROSS_LEVERAGE,
    MAX_SINGLE_ASSET_WEIGHT,
    _LEVERAGE_TOLERANCE,
)


def enforce_risk_limits(
    weights: Mapping[str, float],
    *,
    max_gross_leverage: float = MAX_GROSS_LEVERAGE,
    max_single_weight: float = MAX_SINGLE_ASSET_WEIGHT,
) -> dict[str, float]:
    """Clip and renormalize ``weights`` to satisfy both risk limits.

    Args:
        weights: Raw target weights (long positive, short negative).
        max_gross_leverage: Maximum sum of absolute weights allowed.
        max_single_weight: Maximum absolute weight per symbol allowed.

    Returns:
        Risk-compliant weights dictionary with zero weights removed.

    Raises:
        ValueError: If either risk limit is not positive.
    """
    if max_gross_leverage <= 0:
        raise ValueError("max_gross_leverage must be positive")
    if max_single_weight <= 0:
        raise ValueError("max_single_weight must be positive")

    # 1. Clip individual weights.
    clipped: dict[str, float] = {}
    for symbol, raw in weights.items():
        w = float(raw)
        if w > 0:
            clipped[symbol] = min(w, max_single_weight)
        elif w < 0:
            clipped[symbol] = max(w, -max_single_weight)
        else:
            clipped[symbol] = 0.0

    # 2. Renormalize if gross leverage exceeds the cap.
    gross = sum(abs(w) for w in clipped.values())
    if gross > max_gross_leverage + _LEVERAGE_TOLERANCE:
        scale = max_gross_leverage / gross
        clipped = {symbol: w * scale for symbol, w in clipped.items()}

    # 3. Drop zeros (within tolerance).
    return {symbol: w for symbol, w in clipped.items() if abs(w) > _LEVERAGE_TOLERANCE}


def compute_live_gate_satisfied(
    data_mode: str,
    net_return: float,
    meets_risk_limits: bool,
    is_complete: bool,
) -> bool:
    """Return honest LIVE readiness flag: real_asof AND return > 0 AND risk AND complete.

    This is a *readiness* flag only; ``live_eligible`` is controlled separately by
    the LIVE promotion ticket and owner policy.
    """
    return (
        data_mode == "real_asof"
        and net_return > 0
        and meets_risk_limits
        and is_complete
    )
