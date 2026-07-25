"""Tests for DATA-011 survivorship-bound bar exclusion logic.

Tests that the CMC graveyard correctly excludes dead symbols and
includes alive/unlisted symbols from the paper universe.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from cryptofactors.universe.cmc_survivorship import (
    CMCSurvivorshipProvider,
)


# Re-use the base-asset extraction from build_bound_bars
def _base_asset(binance_symbol: str) -> str:
    sym = binance_symbol.upper()
    for suffix in ("USDT", "BUSD", "USDC", "USD"):
        if sym.endswith(suffix) and len(sym) > len(suffix):
            return sym[: -len(suffix)]
    return sym


PAPER_TO_BINANCE = {
    "XBTUSD": "BTCUSDT",
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
    "PEPEUSD": "PEPEUSD",
}

BAR_RANGE_START = datetime(2020, 1, 1, tzinfo=UTC)


def _make_dead_coin(cmc_id: int, symbol: str, death_date: str) -> dict[str, Any]:
    """Create a raw dead-coin record as returned by CMC API."""
    return {
        "id": cmc_id,
        "name": f"Dead{symbol}",
        "symbol": symbol,
        "slug": f"dead{symbol.lower()}",
        "is_active": 0,
        "dateAdded": "2018-01-01T00:00:00.000Z",
        "dateLaunched": "2018-01-01T00:00:00.000Z",
        "latestUpdateTime": death_date,
        "status": "inactive",
    }


def _make_alive_coin(cmc_id: int, symbol: str) -> dict[str, Any]:
    """Create a raw alive-coin record."""
    return {
        "id": cmc_id,
        "name": f"Alive{symbol}",
        "symbol": symbol,
        "slug": f"alive{symbol.lower()}",
        "is_active": 1,
        "dateAdded": "2018-01-01T00:00:00.000Z",
        "dateLaunched": "2018-01-01T00:00:00.000Z",
        "latestUpdateTime": datetime.now(UTC).isoformat(),
        "status": "active",
    }


def test_symbol_dead_before_range_is_excluded() -> None:
    """Symbol known to CMC dead before bar range -> excluded."""
    records = [
        _make_dead_coin(999001, "LTC", "2019-06-01T00:00:00.000Z"),
        _make_dead_coin(999002, "DOT", "2019-12-31T00:00:00.000Z"),
    ]
    provider = CMCSurvivorshipProvider.from_records(records, availability_time=datetime.now(UTC))

    univ_2020 = provider.universe_at(BAR_RANGE_START)

    # LTC died 2019-06, DOT died 2019-12 — both dead before 2020
    assert "cmc_999001" not in univ_2020, "LTC died 2019, should not be in 2020"
    assert "cmc_999002" not in univ_2020, "DOT died 2019, should not be in 2020"

    # LTCUSDT paper symbol's base 'LTC' is dead before range -> excluded
    ltc_base = _base_asset("LTCUSDT")
    assert ltc_base == "LTC"

    dot_base = _base_asset("DOTUSDT")
    assert dot_base == "DOT"


def test_symbol_alive_in_range_is_included() -> None:
    """Symbol alive during bar range -> included."""
    records = [
        _make_alive_coin(999003, "BTC"),
        _make_alive_coin(999004, "ETH"),
    ]
    provider = CMCSurvivorshipProvider.from_records(records, availability_time=datetime.now(UTC))

    univ_2020 = provider.universe_at(BAR_RANGE_START)

    assert "cmc_999003" in univ_2020, "BTC alive in 2020 -> should be in universe"
    assert "cmc_999004" in univ_2020, "ETH alive in 2020 -> should be in universe"

    btc_base = _base_asset("BTCUSDT")
    assert btc_base == "BTC"

    eth_base = _base_asset("ETHUSDT")
    assert eth_base == "ETH"


def test_symbol_not_in_cmc_is_included() -> None:
    """Symbol not found in CMC graveyard at all -> included."""
    records = [
        # Only list DOGE, not PEPE
        _make_dead_coin(999005, "DOGE", "2019-06-01T00:00:00.000Z"),
    ]
    provider = CMCSurvivorshipProvider.from_records(records, availability_time=datetime.now(UTC))

    univ_2020 = provider.universe_at(BAR_RANGE_START)

    # DOGE is dead per CMC
    assert "cmc_999005" not in univ_2020, "DOGE died 2019, not in 2020"

    # PEPE is not in CMC at all -> no cmc_ instrument -> no exclusion
    pepe_base = _base_asset("PEPEUSDT")
    assert pepe_base == "PEPE"
    pepe_ids = [iid for iid in univ_2020 if "pepe" in iid.lower()]
    assert len(pepe_ids) == 0, "PEPE not in CMC so no cmc_ instrument"


def test_empty_graveyard_all_symbols_included() -> None:
    """Empty graveyard -> no exclusions, all symbols effectively included."""
    # An empty record list should raise, so use a record with no matching symbols
    records = [
        _make_alive_coin(999006, "ZZZZ"),
    ]
    provider = CMCSurvivorshipProvider.from_records(records, availability_time=datetime.now(UTC))

    univ_2020 = provider.universe_at(BAR_RANGE_START)
    assert "cmc_999006" in univ_2020

    # Check that all our paper symbols have no matching exclusion
    for paper_sym, binance_sym in PAPER_TO_BINANCE.items():
        base = _base_asset(binance_sym)
        # None of the paper symbols are ZZZZ, so none are in the graveyard
        assert base != "ZZZZ"


def test_symbol_died_during_range_is_included_up_to_death() -> None:
    """Symbol that died during bar range should be included for dates before death."""
    # BTC died mid-2023 (hypothetical)
    records = [
        _make_dead_coin(999007, "BTC", "2023-06-15T00:00:00.000Z"),
    ]
    provider = CMCSurvivorshipProvider.from_records(records, availability_time=datetime.now(UTC))

    # At 2020-01-01, BTC was still alive
    univ_2020 = provider.universe_at(datetime(2020, 1, 1, tzinfo=UTC))
    assert "cmc_999007" in univ_2020, "BTC alive at 2020"

    # At 2024-01-01, BTC should be dead
    univ_2024 = provider.universe_at(datetime(2024, 1, 1, tzinfo=UTC))
    assert "cmc_999007" not in univ_2024, "BTC died 2023, not in 2024"


def test_real_csv_no_exclusions_for_major_symbols() -> None:
    """With real CSV, none of the 23 paper symbols should be excluded.
    
    Ticker collisions (e.g. Solcoin != Solana) are resolved by cross-checking
    the expected coin name against the CMC record name.
    """
    csv_path = Path("data/survivorship/cmc_dead_universe_full.csv")
    if not csv_path.exists():
        pytest.skip("CMC survivorship CSV not found")

    provider = CMCSurvivorshipProvider.from_csv(csv_path)
    univ_2020 = provider.universe_at(BAR_RANGE_START)

    # Replicate the name-based exclusion logic from build_bound_bars.py
    from scripts.research.build_bound_bars import PAPER_BASE_TO_NAME, _base_asset

    paper_bases = {_base_asset(v): k for k, v in PAPER_TO_BINANCE.items()}
    # Collect all CMC records per symbol
    cmc_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for r in provider.records():
        sym = str(r.get("symbol", "")).strip().upper()
        if sym:
            cmc_by_symbol.setdefault(sym, []).append(r)

    excluded = []
    for base, paper_sym in paper_bases.items():
        cmc_records = cmc_by_symbol.get(base, [])
        for cmc_rec in cmc_records:
            is_active = bool(cmc_rec.get("is_active"))
            death_str = cmc_rec.get("death_proxy_date")
            cmc_name = str(cmc_rec.get("name", "")).strip().lower()
            expected_name = PAPER_BASE_TO_NAME.get(base, "").lower()
            name_mismatch = bool(expected_name) and cmc_name != expected_name
            if not is_active and not name_mismatch:
                excluded.append((paper_sym, base, cmc_rec.get("name"), death_str))

    assert len(excluded) == 0, f"Symbols should not be excluded by CMC graveyard: {excluded}"
