"""DATA-003 — Symbol Mapping between paper universe and venue/canonical bar keys.

Canonical bars from `publish_canonical_bars` use integer `instrument_id` surrogates
in the Parquet column and partition metadata. `CatalogAsOfStore._latest_market_bars`
converts keys via `int(k)`. Paper universe symbols are strings like 'XBTUSD'.

This module provides the end-to-end int instrument_id map (paper symbol → int id)
and a wrapping as-of adapter that transparently translates paper symbol keys to
int ids before calling the underlying `CatalogAsOfStore`.

Fail-closed: `to_instrument_id()` raises `KeyError` if the symbol is unmapped.

Dynamic registry:
  The base maps below (23 symbols, stable IDs 1-23) are the bootstrap anchor.
  All additional symbols are persisted in `data/symbol_registry.json` and loaded
  at import time.  Run `register_symbol()` or the Binance discovery script to add
  new symbols — never edit the base dicts by hand.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa

# ---------------------------------------------------------------------------
# Bootstrap base maps (23 symbols, instrument IDs 1-23, stable forever)
# ---------------------------------------------------------------------------

PAPER_TO_BINANCE_MAP: dict[str, str] = {
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
    "DOGEUSD": "DOGEUSDT",
    "UNIUSD": "UNIUSDT",
    "AAVEUSD": "AAVEUSDT",
    "CRVUSD": "CRVUSDT",
    "APEUSD": "APEUSDT",
    "NEARUSD": "NEARUSDT",
    "FILUSD": "FILUSDT",
    "ARBUSD": "ARBUSDT",
    "OPUSD": "OPUSDT",
    "SUIUSD": "SUIUSDT",
    "SEIUSD": "SEIUSDT",
    "WLDUSD": "WLDUSDT",
    "PEPEUSD": "PEPEUSDT",
}

BINANCE_TO_PAPER_MAP: dict[str, str] = {
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
    "DOGEUSDT": "DOGEUSD",
    "UNIUSDT": "UNIUSD",
    "AAVEUSDT": "AAVEUSD",
    "CRVUSDT": "CRVUSD",
    "APEUSDT": "APEUSD",
    "NEARUSDT": "NEARUSD",
    "FILUSDT": "FILUSD",
    "ARBUSDT": "ARBUSD",
    "OPUSDT": "OPUSD",
    "SUIUSDT": "SUIUSD",
    "SEIUSDT": "SEIUSD",
    "WLDUSDT": "WLDUSD",
    "PEPEUSDT": "PEPEUSD",
}

PAPER_TO_INSTRUMENT_ID: dict[str, int] = {
    "XBTUSD": 1,
    "ETHUSD": 2,
    "SOLUSD": 3,
    "XRPUSD": 4,
    "ADAUSD": 5,
    "AVAXUSD": 6,
    "DOTUSD": 7,
    "LINKUSD": 8,
    "LTCUSD": 9,
    "BCHUSD": 10,
    "DOGEUSD": 11,
    "UNIUSD": 12,
    "AAVEUSD": 13,
    "CRVUSD": 14,
    "APEUSD": 15,
    "NEARUSD": 16,
    "FILUSD": 17,
    "ARBUSD": 18,
    "OPUSD": 19,
    "SUIUSD": 20,
    "SEIUSD": 21,
    "WLDUSD": 22,
    "PEPEUSD": 23,
}

INSTRUMENT_ID_TO_PAPER: dict[int, str] = {v: k for k, v in PAPER_TO_INSTRUMENT_ID.items()}

# ---------------------------------------------------------------------------
# Dynamic symbol registry — loaded from disk at import time
# ---------------------------------------------------------------------------

_REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "symbol_registry.json"


def register_symbol(paper: str, binance: str, instrument_id: int) -> None:
    """Add a symbol to the runtime maps."""
    PAPER_TO_BINANCE_MAP[paper] = binance
    BINANCE_TO_PAPER_MAP[binance] = paper
    PAPER_TO_INSTRUMENT_ID[paper] = instrument_id
    INSTRUMENT_ID_TO_PAPER[instrument_id] = paper


def _load_registry() -> None:
    if not _REGISTRY_PATH.exists():
        return
    try:
        data = json.loads(_REGISTRY_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return
    for entry in data.get("symbols", []):
        paper = entry.get("paper")
        binance = entry.get("binance")
        iid = entry.get("instrument_id")
        if paper and binance and iid and paper not in PAPER_TO_BINANCE_MAP:
            register_symbol(paper, binance, iid)


def _dump_registry() -> None:
    """Persist current full maps to disk."""
    symbols = sorted(
        (p, b, i)
        for p, b in PAPER_TO_BINANCE_MAP.items()
        for i in [PAPER_TO_INSTRUMENT_ID.get(p, 0)]
        if i
    )
    entries: list[dict] = [
        {"paper": p, "binance": b, "instrument_id": i}
        for p, b, i in symbols
    ]
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REGISTRY_PATH.write_text(json.dumps({"symbols": entries}, indent=2))


# Auto-load registry on import
_load_registry()


def to_binance_symbol(symbol: str) -> str:
    """Map paper or generic symbol to Binance spot symbol."""
    sym_clean = symbol.strip().upper()
    return PAPER_TO_BINANCE_MAP.get(sym_clean, sym_clean)


def to_paper_symbol(symbol: str) -> str:
    """Map Binance spot symbol to paper universe symbol."""
    sym_clean = symbol.strip().upper()
    return BINANCE_TO_PAPER_MAP.get(sym_clean, sym_clean)


def to_instrument_id(symbol: str) -> int:
    """Map paper universe symbol to integer instrument_id used in canonical bars.

    Raises ``KeyError`` if symbol is not in the map (fail-closed).
    """
    sym_clean = symbol.strip().upper()
    if sym_clean in PAPER_TO_INSTRUMENT_ID:
        return PAPER_TO_INSTRUMENT_ID[sym_clean]
    raise KeyError(f"Symbol {symbol!r} not in PAPER_TO_INSTRUMENT_ID map; cannot resolve to int instrument_id")


def from_instrument_id(instrument_id: int) -> str:
    """Map integer instrument_id back to paper universe symbol.

    Raises ``KeyError`` if id is not in the map (fail-closed).
    """
    iid = int(instrument_id)
    if iid in INSTRUMENT_ID_TO_PAPER:
        return INSTRUMENT_ID_TO_PAPER[iid]
    raise KeyError(f"instrument_id {instrument_id} not in INSTRUMENT_ID_TO_PAPER map; cannot resolve to paper symbol")


def translate_keys_to_int(keys: Sequence[int | str]) -> list[int]:
    """Translate a sequence of paper symbols or ints to int ids for CatalogAsOfStore.

    If a key is already an int, pass through. If it's a paper symbol, look it up.
    Raises ``KeyError`` if a string key is not in the map (fail-closed).
    """
    result: list[int] = []
    for k in keys:
        if isinstance(k, int) and not isinstance(k, bool):
            result.append(k)
        elif isinstance(k, str):
            result.append(to_instrument_id(k))
        else:
            raise TypeError(f"key must be int or str, got {type(k).__name__}: {k!r}")
    return result


class PaperSymbolAsOfAdapter:
    """Wraps a CatalogAsOfStore to transparently translate paper symbol keys → int instrument_ids.

    The factor and price-lookup code work with paper universe symbols (e.g. 'XBTUSD').
    Canonical bars from `publish_canonical_bars` use integer `instrument_id` surrogates.
    This adapter translates symbol keys to int ids before calling the underlying store,
    and translates the returned `instrument_id` column back to paper symbols.
    """

    def __init__(self, inner_store: Any) -> None:
        self._inner: Any = inner_store

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> Any:
        int_keys = translate_keys_to_int(keys)
        table = self._inner.latest_available(
            dataset_id,
            int_keys,
            fields,
            decision_time,
            max_age,
        )
        return self._maybe_translate_instrument_id(table)

    def as_of(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        knowledge_time: datetime | None = None,
    ) -> Any:
        int_keys = translate_keys_to_int(keys)
        table = self._inner.as_of(
            dataset_id,
            int_keys,
            fields,
            decision_time,
            knowledge_time,
        )
        return self._maybe_translate_instrument_id(table)

    @staticmethod
    def _maybe_translate_instrument_id(table: Any) -> Any:
        """If the table has an 'instrument_id' column with int values, translate to paper symbols."""
        if table is None or getattr(table, "num_rows", 0) == 0:
            return table
        col_names = list(getattr(table, "column_names", []))
        if "instrument_id" not in col_names:
            return table
        old_vals = table.column("instrument_id").to_pylist()
        new_vals: list[str | Any] = []
        translated = False
        for v in old_vals:
            if v is None:
                new_vals.append(v)
            else:
                try:
                    iid = int(v)
                    new_vals.append(INSTRUMENT_ID_TO_PAPER.get(iid, str(v)))
                    translated = True
                except (ValueError, TypeError):
                    new_vals.append(v)
        if not translated:
            return table
        idx = col_names.index("instrument_id")
        return table.set_column(idx, "instrument_id", pa.array(new_vals, type=pa.string()))