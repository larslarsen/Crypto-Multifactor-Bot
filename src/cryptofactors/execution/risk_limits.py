"""ALLOC-001 — Neutrality-preserving paper allocation risk enforcement.

Maps raw target weights into a risk-compliant set before ``PaperBroker.rebalance``.

Policy (per PAPER-006 / AUD-006 + ALLOC-001):
1. Clip each single-asset weight to ``[-max_single_weight, max_single_weight]``.
2. Preserve dollar-neutrality when the input has both long and short legs:
   after clipping, rescale the *long leg* and the *short leg* independently so
   that ``sum(long) == sum(|short|)`` (net exposure ≈ 0) while keeping each
   leg within ``max_gross_leverage / 2``. This prevents the net-exposure drift
   that the previous uniform rescale introduced.
3. Directional books (only one leg) cannot be made neutral; they are scaled to
   fit within ``max_gross_leverage`` with a documented residual net exposure.
4. Drop zero/rounded-to-zero weights from the returned dict.

This is *enforcement* (clip + leg-rescale), not validation. The live path uses
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

__all__ = [
    "MAX_GROSS_LEVERAGE",
    "MAX_SINGLE_ASSET_WEIGHT",
    "enforce_risk_limits",
    "compute_live_gate_satisfied",
]


def enforce_risk_limits(
    weights: Mapping[str, float],
    *,
    max_gross_leverage: float = MAX_GROSS_LEVERAGE,
    max_single_weight: float = MAX_SINGLE_ASSET_WEIGHT,
    net_exposure_tolerance: float = 1e-6,
) -> dict[str, float]:
    """Clip and rescale ``weights`` to satisfy both risk limits while preserving neutrality.

    Args:
        weights: Raw target weights (long positive, short negative).
        max_gross_leverage: Maximum sum of absolute weights allowed.
        max_single_weight: Maximum absolute weight per symbol allowed.
        net_exposure_tolerance: Tolerance used when testing net exposure for zero.

    Returns:
        Risk-compliant weights dictionary with zero weights removed.

    Raises:
        ValueError: If either risk limit is not positive.
    """
    if max_gross_leverage <= 0:
        raise ValueError("max_gross_leverage must be positive")
    if max_single_weight <= 0:
        raise ValueError("max_single_weight must be positive")
    if net_exposure_tolerance < 0:
        raise ValueError("net_exposure_tolerance must be non-negative")

    # 1. Clip individual weights.
    long: dict[str, float] = {}
    short: dict[str, float] = {}
    for symbol, raw in weights.items():
        w = float(raw)
        if w > 0:
            long[symbol] = min(w, max_single_weight)
        elif w < 0:
            short[symbol] = max(w, -max_single_weight)

    long_gross = sum(long.values())
    short_gross = sum(abs(w) for w in short.values())
    result: dict[str, float]

    if long_gross > _LEVERAGE_TOLERANCE and short_gross > _LEVERAGE_TOLERANCE:
        # 2a. Neutral L/S book: rescale long and short legs independently to
        # restore equal long/short gross while respecting the total gross cap.
        target_leg_gross = min(long_gross, short_gross, max_gross_leverage / 2.0)
        if long_gross > target_leg_gross + _LEVERAGE_TOLERANCE:
            scale = target_leg_gross / long_gross
            long = {symbol: w * scale for symbol, w in long.items()}
        if short_gross > target_leg_gross + _LEVERAGE_TOLERANCE:
            scale = target_leg_gross / short_gross
            short = {symbol: w * scale for symbol, w in short.items()}
        result = {**long, **short}
    else:
        # 2b. Directional book: cannot be neutral. Scale the whole book to fit
        # the gross cap (already clipped per name). Residual net is documented.
        clipped = {**long, **short}
        gross = long_gross + short_gross
        if gross > max_gross_leverage + _LEVERAGE_TOLERANCE:
            scale = max_gross_leverage / gross
            result = {symbol: w * scale for symbol, w in clipped.items()}
        else:
            result = clipped

    # 3. Drop zeros (within tolerance).
    return {symbol: w for symbol, w in result.items() if abs(w) > _LEVERAGE_TOLERANCE}


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
