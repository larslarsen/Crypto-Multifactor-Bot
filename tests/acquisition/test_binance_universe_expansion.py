"""Tests for DATA-008 Binance universe expansion helpers.

All network calls are mocked; no API keys required in CI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from cryptofactors.acquisition.binance_universe_expansion import (
    BinanceSymbolScreener,
    BinanceUniverseExpander,
    DailySymbolBudget,
    IncrementalWatermarkStore,
    InstrumentIdAllocator,
    RateLimitIncident,
    load_watermark_as_datetime,
)
from cryptofactors.execution.symbols import PAPER_TO_INSTRUMENT_ID


UTC = timezone.utc


def sample_ticker(symbol: str, quote_volume: float) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "status": "TRADING",
        "quoteVolume": str(quote_volume),
        "lastPrice": "100.0",
        "count": 10000,
    }


class TestBinanceSymbolScreener:
    def test_screen_usdt_spot_filters_non_usdt(self) -> None:
        screener = BinanceSymbolScreener()
        tickers = [
            sample_ticker("BTCUSDT", 1_000_000_000),
            sample_ticker("ETHBTC", 500_000_000),
            sample_ticker("BTCUSDC", 100_000_000),
        ]
        screened = screener.screen_usdt_spot(tickers)
        symbols = {s.symbol for s in screened}
        assert symbols == {"BTCUSDT"}

    def test_screen_excludes_leveraged_tokens(self) -> None:
        screener = BinanceSymbolScreener()
        tickers = [
            sample_ticker("BTCUPUSDT", 1_000_000_000),
            sample_ticker("BTCDOWNUSDT", 500_000_000),
            sample_ticker("BTCUSDT", 100_000_000),
        ]
        screened = screener.screen_usdt_spot(tickers)
        symbols = {s.symbol for s in screened}
        assert symbols == {"BTCUSDT"}

    def test_screen_excludes_stablecoin_pairs(self) -> None:
        screener = BinanceSymbolScreener()
        tickers = [
            sample_ticker("USDCUSDT", 1_000_000_000),
            sample_ticker("BTCUSDT", 100_000_000),
        ]
        screened = screener.screen_usdt_spot(tickers)
        symbols = {s.symbol for s in screened}
        assert symbols == {"BTCUSDT"}

    def test_screen_volume_floor(self) -> None:
        screener = BinanceSymbolScreener(min_quote_volume_usdt=1_000_000)
        tickers = [
            sample_ticker("BTCUSDT", 2_000_000),
            sample_ticker("ETHUSDT", 500_000),
        ]
        screened = screener.screen_usdt_spot(tickers)
        symbols = {s.symbol for s in screened}
        assert symbols == {"BTCUSDT"}

    def test_prioritize_excludes_existing_and_sorts(self) -> None:
        from cryptofactors.acquisition.binance_universe_expansion import SymbolPriority
        screener = BinanceSymbolScreener()
        screened = [
            SymbolPriority(symbol="BTCUSDT", quote_volume=1_000_000, price=100.0, count=1000),
            SymbolPriority(symbol="ETHUSDT", quote_volume=2_000_000, price=100.0, count=1000),
            SymbolPriority(symbol="SOLUSDT", quote_volume=3_000_000, price=100.0, count=1000),
        ]
        result = screener.prioritize(screened, existing_symbols=["BTCUSDT"], top_n=2)
        assert result == ["SOLUSDT", "ETHUSDT"]

    def test_fetch_24hr_tickers_with_mock_client(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[sample_ticker("BTCUSDT", 1_000_000)])

        client = httpx.Client(transport=httpx.MockTransport(handler))
        screener = BinanceSymbolScreener(client=client)
        data = screener.fetch_24hr_tickers()
        assert len(data) == 1
        assert data[0]["symbol"] == "BTCUSDT"


class TestIncrementalWatermarkStore:
    def test_save_and_load(self, tmp_path: Path) -> None:
        path = tmp_path / "watermarks.json"
        store = IncrementalWatermarkStore(path)
        store.save({"BTCUSDT": "2026-07-24T00:00:00+00:00"})
        loaded = store.load()
        assert loaded == {"BTCUSDT": "2026-07-24T00:00:00+00:00"}

    def test_load_missing_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.json"
        store = IncrementalWatermarkStore(path)
        assert store.load() == {}

    def test_load_merges_with_existing(self, tmp_path: Path) -> None:
        path = tmp_path / "watermarks.json"
        path.write_text('{"other": "data"}')
        store = IncrementalWatermarkStore(path)
        store.save({"BTCUSDT": "2026-07-24T00:00:00+00:00"})
        text = path.read_text()
        data = __import__("json").loads(text)
        assert data["binance_spot"]["BTCUSDT"] == "2026-07-24T00:00:00+00:00"
        assert data["other"] == "data"


class TestDailySymbolBudget:
    def test_can_process_within_budget(self) -> None:
        budget = DailySymbolBudget(symbols_per_day=5)
        assert budget.can_process() is True
        budget.record_processed()
        assert budget.remaining_today() == 4

    def test_stops_at_budget(self) -> None:
        budget = DailySymbolBudget(symbols_per_day=2)
        budget.record_processed()
        budget.record_processed()
        assert budget.can_process() is False
        assert budget.remaining_today() == 0

    def test_records_incidents(self) -> None:
        budget = DailySymbolBudget()
        incident = RateLimitIncident(
            timestamp="2026-07-24T00:00:00+00:00",
            symbol="BTCUSDT",
            status_code=429,
            backoff_seconds=10.0,
            note="test",
        )
        budget.record_incident(incident)
        assert len(budget.to_dict()["incidents"]) == 1


class TestInstrumentIdAllocator:
    def test_allocates_new_ids(self) -> None:
        allocator = InstrumentIdAllocator(PAPER_TO_INSTRUMENT_ID)
        assert allocator.allocate("XBTUSD") == 1
        assert allocator.allocate("NEWUSDT") == 24
        assert allocator.allocate("NEW2USDT") == 25
        assert allocator.get_map()["NEWUSDT"] == 24


class TestWatermarkHelpers:
    def test_load_watermark_returns_default(self) -> None:
        dt = load_watermark_as_datetime({}, "BTCUSDT")
        assert dt == datetime(2020, 1, 1, tzinfo=UTC)

    def test_load_watermark_returns_next_day(self) -> None:
        dt = load_watermark_as_datetime(
            {"BTCUSDT": "2026-07-24T00:00:00+00:00"},
            "BTCUSDT",
        )
        assert dt == datetime(2026, 7, 25, tzinfo=UTC)


class TestBinanceUniverseExpander:
    def test_select_and_plan(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=[
                    sample_ticker("BTCUSDT", 1_000_000),
                    sample_ticker("ETHUSDT", 2_000_000),
                    sample_ticker("SOLUSDT", 3_000_000),
                    sample_ticker("NEWUSDT", 4_000_000),
                ],
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        screener = BinanceSymbolScreener(client=client)
        allocator = InstrumentIdAllocator(PAPER_TO_INSTRUMENT_ID)
        expander = BinanceUniverseExpander(
            screener=screener,
            watermark_store=IncrementalWatermarkStore("/dev/null"),
            budget=DailySymbolBudget(symbols_per_day=10),
            instrument_allocator=allocator,
            base_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            target_start=datetime(2020, 1, 1, tzinfo=UTC),
            target_end=datetime(2026, 7, 24, tzinfo=UTC),
            top_n=10,
        )
        new_symbols = expander.select_new_symbols()
        assert new_symbols == ["NEWUSDT"]
        planned = expander.plan_backfill(new_symbols)
        assert planned == ["NEWUSDT"]
        mapping = expander.allocate_instrument_ids(planned)
        assert mapping["NEWUSDT"] == 24

    def test_plan_respects_budget(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=[
                    sample_ticker("NEW1USDT", 4_000_000),
                    sample_ticker("NEW2USDT", 3_000_000),
                    sample_ticker("NEW3USDT", 2_000_000),
                ],
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        screener = BinanceSymbolScreener(client=client)
        allocator = InstrumentIdAllocator(PAPER_TO_INSTRUMENT_ID)
        expander = BinanceUniverseExpander(
            screener=screener,
            watermark_store=IncrementalWatermarkStore("/dev/null"),
            budget=DailySymbolBudget(symbols_per_day=2),
            instrument_allocator=allocator,
            base_symbols=["BTCUSDT"],
            target_start=datetime(2020, 1, 1, tzinfo=UTC),
            target_end=datetime(2026, 7, 24, tzinfo=UTC),
            top_n=10,
        )
        new_symbols = expander.select_new_symbols()
        planned = expander.plan_backfill(new_symbols)
        assert planned == ["NEW1USDT", "NEW2USDT"]
