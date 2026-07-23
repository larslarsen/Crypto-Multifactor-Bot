"""DATA-003 — Symbol Mapping between paper universe and venue/canonical bar keys."""

from __future__ import annotations

from typing import Final

PAPER_TO_BINANCE_MAP: Final[dict[str, str]] = {
    "XBTUSD": "BTCUSDT",
    "BTCUSD": "BTCUSDT",
    "ETHUSD": "ETHUSDT",
    "SOLUSD": "SOLUSDT",
    "XRPUSD": "XRPUSDT",
    "ADAUSD": "ADAUSDT",
    "AVAXUSD": "AVAXUSDT",
    "DOTUSD": "DOTUSDT",
    "LINKUSD": "LINKUSDT",
    "LTCUSD": "LTCUSDT",
    "BCHUSD": "BCHUSDT",
}

BINANCE_TO_PAPER_MAP: Final[dict[str, str]] = {
    "BTCUSDT": "XBTUSD",
    "ETHUSDT": "ETHUSD",
    "SOLUSDT": "SOLUSD",
    "XRPUSDT": "XRPUSD",
    "ADAUSDT": "ADAUSD",
    "AVAXUSDT": "AVAXUSD",
    "DOTUSDT": "DOTUSD",
    "LINKUSDT": "LINKUSD",
    "LTCUSDT": "LTCUSD",
    "BCHUSDT": "BCHUSD",
}


def to_binance_symbol(symbol: str) -> str:
    """Map paper or generic symbol to Binance spot symbol."""
    sym_clean = symbol.strip().upper()
    return PAPER_TO_BINANCE_MAP.get(sym_clean, sym_clean)


def to_paper_symbol(symbol: str) -> str:
    """Map Binance spot symbol to paper universe symbol."""
    sym_clean = symbol.strip().upper()
    return BINANCE_TO_PAPER_MAP.get(sym_clean, sym_clean)
