"""DATA-008 — tests for Binance spot universe expansion.

Every test drives the shipped implementation: `binance_universe`, `binance_snapshot`,
and the runner `scripts/research/binance_universe_expansion.py`. Publication is proven
by running the runner, not by reimplementing it.

No test may reach the network: every HTTP path goes through an injected
`MockTransport`, and `forbid_real_network` fails any attempt to build a bare client.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pyarrow.parquet as pq
import pytest

from cryptofactors.acquisition.binance_snapshot import (
    BinanceBarAcquirer,
    BinanceSnapshotError,
    KlineBar,
    SymbolState,
    WatermarkStore,
    bars_from_records,
    merge_canonical_bars,
    missing_days,
    parse_klines,
    resume_start,
    symbol_covers_range,
)
from cryptofactors.acquisition.binance_universe import (
    EXCLUSION_TAXONOMY_VERSION,
    VOLUME_WINDOW,
    BinanceUniverseAcquirer,
    BinanceUniverseError,
    DeferralReason,
    ExclusionReason,
    SelectionConfig,
    classify_base_asset,
    evaluate_history,
    is_leveraged_token,
    parse_exchange_info,
    parse_first_kline_open_time,
    parse_ticker_evidence,
    rank_symbols,
    select_symbols,
)
from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations
from cryptofactors.ingest import raw_http
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.paths import content_addressed_absolute_path
from cryptofactors.ingest.raw.writer import RawObjectWriter
from cryptofactors.ingest.raw_http import AcquisitionLog, RawHttpAcquirer

REAL_HTTPX_CLIENT = httpx.Client

DAY0 = datetime(2026, 6, 1, tzinfo=UTC)
END_TIME = DAY0 + timedelta(days=4)
OLD_LISTING_MS = int(datetime(2020, 1, 1, tzinfo=UTC).timestamp() * 1000)
NEW_LISTING_MS = int(datetime(2026, 5, 1, tzinfo=UTC).timestamp() * 1000)


def day(index: int) -> datetime:
    return DAY0 + timedelta(days=index)


def kline(index: int, *, close: float = 100.0) -> list[Any]:
    """[openTime, open, high, low, close, volume, closeTime, quoteVolume, trades]."""
    open_ms = int(day(index).timestamp() * 1000)
    return [
        open_ms, str(close), str(close + 1), str(close - 1), str(close), "10.5",
        open_ms + 86_399_999, "1050.0", 42,
    ]


@pytest.fixture(autouse=True)
def forbid_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test in this module may contact a public endpoint."""
    def guarded(*args: Any, **kwargs: Any) -> httpx.Client:
        if kwargs.get("transport") is None:
            raise AssertionError("a real network client was requested; use the mock transport")
        return REAL_HTTPX_CLIENT(*args, **kwargs)

    monkeypatch.setattr(raw_http.httpx, "Client", guarded)


def spot_entry(
    symbol: str,
    base: str,
    quote: str = "USDT",
    *,
    status: str = "TRADING",
    spot: bool = True,
    permissions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "symbol": symbol, "baseAsset": base, "quoteAsset": quote, "status": status,
        "isSpotTradingAllowed": spot, "permissions": permissions or ["SPOT"],
    }


DEFAULT_SYMBOLS = [
    spot_entry("BTCUSDT", "BTC"),
    spot_entry("ETHUSDT", "ETH"),
    spot_entry("SUPERUSDT", "SUPER"),
    spot_entry("JUPUSDT", "JUP"),
]


class MockBinance:
    """Serves exchangeInfo, ticker/24hr and klines from in-memory fixtures."""

    def __init__(
        self,
        *,
        symbols: list[dict[str, Any]] | None = None,
        volumes: dict[str, float] | None = None,
        klines_by_symbol: dict[str, list[list[Any]]] | None = None,
        first_kline_ms: dict[str, int] | None = None,
        default_first_kline_ms: int = OLD_LISTING_MS,
        klines_status: int = 200,
        klines_status_by_symbol: dict[str, int] | None = None,
        klines_transport_error_for: set[str] | None = None,
        history_status_by_symbol: dict[str, int] | None = None,
        exchange_info_status: int = 200,
        ticker_status: int = 200,
        default_volume: float = 5_000_000.0,
    ) -> None:
        self.symbols = symbols if symbols is not None else list(DEFAULT_SYMBOLS)
        self.volumes = volumes or {}
        self.klines_by_symbol = klines_by_symbol or {}
        self.first_kline_ms = first_kline_ms or {}
        self.default_first_kline_ms = default_first_kline_ms
        self.klines_status = klines_status
        self.klines_status_by_symbol = klines_status_by_symbol or {}
        self.klines_transport_error_for = klines_transport_error_for or set()
        self.history_status_by_symbol = history_status_by_symbol or {}
        self.exchange_info_status = exchange_info_status
        self.ticker_status = ticker_status
        self.default_volume = default_volume
        self.requests: list[str] = []
        self.served: list[bytes] = []

    def _respond(self, status: int, payload: Any) -> httpx.Response:
        body = json.dumps(payload).encode()
        self.served.append(body)
        return httpx.Response(status, content=body, headers={"content-type": "application/json"})

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)

        if "exchangeInfo" in url:
            if self.exchange_info_status != 200:
                return self._respond(self.exchange_info_status, {"code": -1})
            return self._respond(200, {"symbols": self.symbols})

        if "ticker/24hr" in url:
            if self.ticker_status != 200:
                return self._respond(self.ticker_status, {"code": -1})
            return self._respond(200, [
                {
                    "symbol": entry["symbol"],
                    "quoteVolume": str(self.volumes.get(entry["symbol"], self.default_volume)),
                    "count": "1000",
                }
                for entry in self.symbols
            ])

        if "klines" in url:
            params = dict(request.url.params)
            symbol = params.get("symbol", "")
            # startTime=0 is the history-eligibility probe, not the bar fetch.
            is_probe = params.get("startTime") == "0"
            if is_probe:
                status = self.history_status_by_symbol.get(symbol, 200)
                if status != 200:
                    return self._respond(status, {"code": -1})
            else:
                if symbol in self.klines_transport_error_for:
                    raise httpx.ConnectError("klines refused", request=request)
                status = self.klines_status_by_symbol.get(symbol, self.klines_status)
                if status != 200:
                    return self._respond(status, {"code": -1})
            if is_probe:
                first_ms = self.first_kline_ms.get(symbol, self.default_first_kline_ms)
                if first_ms < 0:
                    return self._respond(200, [])
                return self._respond(200, [[first_ms, "1", "1", "1", "1", "1", 0, "1", 1]])
            rows = self.klines_by_symbol.get(symbol, [kline(i) for i in range(5)])
            return self._respond(200, rows)

        return self._respond(404, {"code": -1})

    def client(self) -> httpx.Client:
        return REAL_HTTPX_CLIENT(transport=httpx.MockTransport(self.handler))

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            raw_http.httpx, "Client",
            lambda **_kw: REAL_HTTPX_CLIENT(transport=httpx.MockTransport(self.handler)),
        )


class Store:
    def __init__(self, tmp_path: Path) -> None:
        self.store_root = tmp_path / "store"
        self.raw_root = self.store_root / "raw"
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.db = tmp_path / "control.db"
        self.watermark_path = tmp_path / "watermarks.json"
        apply_migrations(self.db, migrations_dir=MIGRATIONS_DIR)
        self.catalog = SqliteRawObjectCatalog(self.db)
        self.writer = RawObjectWriter(RawObjectStoreConfig(root=self.raw_root), self.catalog)

    def close(self) -> None:
        self.catalog.close()

    def raw_path(self, raw_object_id: str) -> Path:
        return content_addressed_absolute_path(self.raw_root, raw_object_id.removeprefix("raw_"))


@pytest.fixture
def store(tmp_path: Path) -> Iterator[Store]:
    created = Store(tmp_path)
    yield created
    created.close()


def make_acquirer(store: Store, node: MockBinance, **kwargs: Any) -> RawHttpAcquirer:
    return RawHttpAcquirer(
        raw_writer=store.writer, client=node.client(), log=AcquisitionLog(), **kwargs
    )


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

class TestDiscovery:
    def test_symbol_facts_come_from_exchange_info(self) -> None:
        parsed = parse_exchange_info({"symbols": DEFAULT_SYMBOLS}, raw_object_id="raw_a")

        assert [s.symbol for s in parsed] == ["BTCUSDT", "ETHUSDT", "JUPUSDT", "SUPERUSDT"]
        btc = next(s for s in parsed if s.symbol == "BTCUSDT")
        assert (btc.base_asset, btc.quote_asset, btc.status) == ("BTC", "USDT", "TRADING")
        assert btc.raw_object_id == "raw_a"

    def test_quote_asset_is_stated_not_sliced_from_the_symbol(self) -> None:
        """String slicing cannot tell BTCUSDT (USDT) from a base ending in USD."""
        parsed = parse_exchange_info(
            {"symbols": [spot_entry("BTCUSDC", "BTC", "USDC")]}, raw_object_id="raw_a"
        )

        assert parsed[0].quote_asset == "USDC"

    @pytest.mark.parametrize("missing", ["symbol", "baseAsset", "quoteAsset", "status"])
    def test_a_symbol_entry_missing_a_stated_fact_is_refused(self, missing: str) -> None:
        entry = spot_entry("BTCUSDT", "BTC")
        del entry[missing]
        with pytest.raises(BinanceUniverseError, match=f"missing '{missing}'"):
            parse_exchange_info({"symbols": [entry]}, raw_object_id="raw_a")

    def test_a_repeated_symbol_is_refused(self) -> None:
        with pytest.raises(BinanceUniverseError, match="repeats symbol"):
            parse_exchange_info(
                {"symbols": [spot_entry("BTCUSDT", "BTC"), spot_entry("BTCUSDT", "BTC")]},
                raw_object_id="raw_a",
            )

    def test_a_non_object_payload_is_refused(self) -> None:
        with pytest.raises(BinanceUniverseError, match="must be a JSON object"):
            parse_exchange_info([], raw_object_id="raw_a")


# ---------------------------------------------------------------------------
# Leveraged-token classification
# ---------------------------------------------------------------------------

class TestLeveragedTokenParsing:
    KNOWN = ["BTC", "ETH", "SUPER", "JUP", "TRUMP", "PEPE"]

    @pytest.mark.parametrize("base", ["BTCUP", "BTCDOWN", "ETHBULL", "ETHBEAR"])
    def test_a_leveraged_base_is_detected(self, base: str) -> None:
        assert is_leveraged_token(base, known_bases=self.KNOWN)

    @pytest.mark.parametrize("base", ["SUPER", "JUP", "TRUMP", "BTC", "ETH", "PEPE"])
    def test_an_ordinary_base_is_not_leveraged(self, base: str) -> None:
        """The previous whole-symbol substring scan removed SUPERUSDT and JUPUSDT."""
        assert not is_leveraged_token(base, known_bases=self.KNOWN)

    def test_a_stem_that_is_not_a_listed_base_is_not_leveraged(self) -> None:
        """JUP splits to 'J', which is not an asset, so JUP is ordinary."""
        assert not is_leveraged_token("JUP", known_bases=["BTC", "ETH"])

    def test_permissions_are_authoritative(self) -> None:
        assert is_leveraged_token("WEIRD", permissions=["LEVERAGED"], known_bases=[])

    def test_a_stem_only_counts_when_it_is_listed(self) -> None:
        assert not is_leveraged_token("BTCUP", known_bases=["ETH"])
        assert is_leveraged_token("BTCUP", known_bases=["BTC"])


class TestExclusionTaxonomy:
    @pytest.mark.parametrize(
        ("base", "reason"),
        [
            ("USDC", ExclusionReason.STABLECOIN_BASE),
            ("FDUSD", ExclusionReason.STABLECOIN_BASE),
            ("EUR", ExclusionReason.FIAT_BASE),
            ("TRY", ExclusionReason.FIAT_BASE),
            ("PAXG", ExclusionReason.TOKENIZED_COMMODITY_BASE),
        ],
    )
    def test_non_target_bases_are_classified(
        self, base: str, reason: ExclusionReason
    ) -> None:
        assert classify_base_asset(base) is reason

    @pytest.mark.parametrize("base", ["BTC", "ETH", "SUPER", "JUP", "TRUMP"])
    def test_target_bases_are_unclassified(self, base: str) -> None:
        assert classify_base_asset(base) is None

    def test_the_taxonomy_is_versioned(self) -> None:
        assert EXCLUSION_TAXONOMY_VERSION


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def selection_for(
    entries: list[dict[str, Any]],
    volumes: dict[str, float] | None = None,
    config: SelectionConfig | None = None,
    already_covered: list[str] | None = None,
) -> Any:
    discovered = parse_exchange_info({"symbols": entries}, raw_object_id="raw_a")
    tickers = [
        {"symbol": e["symbol"], "quoteVolume": str((volumes or {}).get(e["symbol"], 5e6)),
         "count": "10"}
        for e in entries
    ]
    evidence = parse_ticker_evidence(tickers, observed_at=DAY0, raw_object_id="raw_b")
    return select_symbols(
        discovered=discovered, evidence=evidence,
        config=config or SelectionConfig(), already_covered=already_covered or [],
    )


class TestSelection:
    def test_ordinary_symbols_containing_up_are_selected(self) -> None:
        result = selection_for(DEFAULT_SYMBOLS)

        assert set(result.symbols) == {"BTCUSDT", "ETHUSDT", "SUPERUSDT", "JUPUSDT"}

    def test_leveraged_tokens_are_excluded_with_a_reason(self) -> None:
        result = selection_for(DEFAULT_SYMBOLS + [spot_entry("BTCUPUSDT", "BTCUP")])

        excluded = {e.symbol: e.reason for e in result.excluded}
        assert excluded["BTCUPUSDT"] is ExclusionReason.LEVERAGED_TOKEN
        assert "BTCUPUSDT" not in result.symbols

    def test_every_exclusion_carries_a_reason_and_taxonomy_version(self) -> None:
        result = selection_for(DEFAULT_SYMBOLS + [
            spot_entry("USDCUSDT", "USDC"), spot_entry("EURUSDT", "EUR"),
        ])

        for excluded in result.excluded:
            assert excluded.reason in set(ExclusionReason)
            assert excluded.detail
            assert excluded.as_dict()["taxonomy_version"] == EXCLUSION_TAXONOMY_VERSION

    def test_a_non_trading_symbol_is_excluded(self) -> None:
        """Status comes from exchangeInfo; /ticker/24hr never reports it."""
        result = selection_for([spot_entry("HALTUSDT", "HALT", status="BREAK")])

        assert {e.reason for e in result.excluded} == {ExclusionReason.NOT_TRADING}

    def test_a_non_spot_symbol_is_excluded(self) -> None:
        result = selection_for([spot_entry("XUSDT", "X", spot=False)])

        assert {e.reason for e in result.excluded} == {ExclusionReason.NOT_SPOT}

    def test_an_untargeted_quote_asset_is_excluded(self) -> None:
        result = selection_for([spot_entry("BTCUSDC", "BTC", "USDC")])

        assert {e.reason for e in result.excluded} == {
            ExclusionReason.QUOTE_ASSET_NOT_TARGETED
        }

    def test_a_symbol_below_the_volume_floor_is_excluded(self) -> None:
        result = selection_for(
            DEFAULT_SYMBOLS, volumes={"JUPUSDT": 1.0},
            config=SelectionConfig(min_quote_volume=1_000_000.0),
        )

        excluded = {e.symbol: e.reason for e in result.excluded}
        assert excluded["JUPUSDT"] is ExclusionReason.BELOW_VOLUME_FLOOR

    def test_a_symbol_with_no_evidence_is_excluded(self) -> None:
        discovered = parse_exchange_info({"symbols": DEFAULT_SYMBOLS}, raw_object_id="raw_a")
        result = select_symbols(discovered=discovered, evidence={}, config=SelectionConfig())

        assert {e.reason for e in result.excluded} == {ExclusionReason.NO_VOLUME_EVIDENCE}

    def test_already_covered_symbols_are_excluded_with_a_reason(self) -> None:
        result = selection_for(DEFAULT_SYMBOLS, already_covered=["BTCUSDT"])

        excluded = {e.symbol: e.reason for e in result.excluded}
        assert excluded["BTCUSDT"] is ExclusionReason.ALREADY_COVERED


class TestDeterministicRanking:
    def test_ranking_is_by_descending_volume(self) -> None:
        result = selection_for(
            DEFAULT_SYMBOLS,
            volumes={"BTCUSDT": 9e9, "ETHUSDT": 5e9, "SUPERUSDT": 2e9, "JUPUSDT": 1e9},
        )

        assert result.symbols == ["BTCUSDT", "ETHUSDT", "SUPERUSDT", "JUPUSDT"]
        assert [r.rank for r in result.ranked] == [1, 2, 3, 4]

    def test_equal_volumes_tie_break_on_symbol(self) -> None:
        """Without an explicit tie-break, equal volumes keep input order."""
        result = selection_for(DEFAULT_SYMBOLS, volumes=dict.fromkeys(
            [e["symbol"] for e in DEFAULT_SYMBOLS], 5e6
        ))

        assert result.symbols == sorted(result.symbols)

    def test_ranking_is_reproducible(self) -> None:
        volumes = {"BTCUSDT": 9e9, "ETHUSDT": 9e9, "SUPERUSDT": 2e9, "JUPUSDT": 2e9}

        first = selection_for(DEFAULT_SYMBOLS, volumes=volumes).symbols
        second = selection_for(list(reversed(DEFAULT_SYMBOLS)), volumes=volumes).symbols

        assert first == second

    def test_evidence_states_its_window_and_lineage(self) -> None:
        result = selection_for(DEFAULT_SYMBOLS)

        for ranked in result.ranked:
            assert ranked.evidence.window == VOLUME_WINDOW == "24h"
            assert ranked.evidence.observed_at == DAY0
            assert ranked.evidence.raw_object_id == "raw_b"

    def test_the_window_is_not_described_as_thirty_days(self) -> None:
        """The ranking evidence is a 24h rolling ticker, and says so."""
        assert VOLUME_WINDOW == "24h"
        assert "30" not in SelectionConfig().as_dict()["volume_window"]

    def test_top_n_truncates_after_ranking(self) -> None:
        result = selection_for(
            DEFAULT_SYMBOLS,
            volumes={"BTCUSDT": 9e9, "ETHUSDT": 5e9, "SUPERUSDT": 2e9, "JUPUSDT": 1e9},
            config=SelectionConfig(top_n=2),
        )

        assert result.symbols == ["BTCUSDT", "ETHUSDT"]

    def test_ranking_an_empty_candidate_set_is_empty(self) -> None:
        assert rank_symbols([]) == []

    def test_equal_volumes_are_ordered_by_symbol_regardless_of_input_order(self) -> None:
        """Directly exercises the tie-break.

        Going through parse_exchange_info cannot prove this: it already returns
        symbols sorted, so a stable sort on volume alone looks identical.
        """
        discovered = parse_exchange_info(
            {"symbols": DEFAULT_SYMBOLS}, raw_object_id="raw_a"
        )
        by_symbol = {item.symbol: item for item in discovered}
        evidence = parse_ticker_evidence(
            [{"symbol": s, "quoteVolume": "5000000", "count": "1"} for s in by_symbol],
            observed_at=DAY0, raw_object_id="raw_b",
        )
        # Deliberately reverse-alphabetical input with identical volumes.
        unsorted = [
            (by_symbol[name], evidence[name])
            for name in ["SUPERUSDT", "JUPUSDT", "ETHUSDT", "BTCUSDT"]
        ]

        ranked = rank_symbols(unsorted)

        assert [r.symbol for r in ranked] == [
            "BTCUSDT", "ETHUSDT", "JUPUSDT", "SUPERUSDT"
        ]


# ---------------------------------------------------------------------------
# History eligibility
# ---------------------------------------------------------------------------

class TestHistoryEligibility:
    def test_a_long_history_symbol_is_eligible(self) -> None:
        verdict = evaluate_history(
            symbol="BTCUSDT", first_open_time=datetime(2020, 1, 1, tzinfo=UTC),
            as_of=END_TIME, min_history_days=365, raw_object_id="raw_a",
        )

        assert verdict.eligible
        assert verdict.reason is None
        assert verdict.history_days is not None and verdict.history_days > 365

    def test_a_recent_listing_is_deferred_not_admitted(self) -> None:
        verdict = evaluate_history(
            symbol="NEWUSDT", first_open_time=datetime(2026, 5, 1, tzinfo=UTC),
            as_of=END_TIME, min_history_days=365, raw_object_id="raw_a",
        )

        assert not verdict.eligible
        assert verdict.reason is DeferralReason.INSUFFICIENT_HISTORY

    def test_unknown_history_is_deferred(self) -> None:
        verdict = evaluate_history(
            symbol="XUSDT", first_open_time=None, as_of=END_TIME,
            min_history_days=365, raw_object_id=None,
        )

        assert not verdict.eligible
        assert verdict.reason is DeferralReason.HISTORY_UNKNOWN

    def test_the_first_kline_open_time_is_decoded(self) -> None:
        moment = parse_first_kline_open_time([[OLD_LISTING_MS, "1", "1", "1", "1", "1"]])

        assert moment == datetime(2020, 1, 1, tzinfo=UTC)

    def test_no_klines_means_no_history(self) -> None:
        assert parse_first_kline_open_time([]) is None

    def test_a_non_list_klines_payload_is_refused(self) -> None:
        with pytest.raises(BinanceUniverseError, match="must be a list"):
            parse_first_kline_open_time({})

    def test_a_failed_history_probe_defers(self, store: Store) -> None:
        node = MockBinance(history_status_by_symbol={"BTCUSDT": 500})
        universe = BinanceUniverseAcquirer(
            acquirer=make_acquirer(store, node), base_url="https://binance.test"
        )

        verdict = universe.fetch_history_eligibility(
            "BTCUSDT", as_of=END_TIME, min_history_days=365
        )

        assert not verdict.eligible
        assert verdict.reason is DeferralReason.HISTORY_UNKNOWN


# ---------------------------------------------------------------------------
# Bars
# ---------------------------------------------------------------------------

class TestBarValidation:
    def _parse(self, rows: list[list[Any]]) -> list[KlineBar]:
        return parse_klines(
            rows, symbol="BTCUSDT", start_time=DAY0, end_time=END_TIME,
            raw_object_id="raw_x",
        )

    def test_valid_klines_decode_in_order(self) -> None:
        bars = self._parse([kline(2), kline(0), kline(1)])

        assert [b.open_time for b in bars] == [day(0), day(1), day(2)]
        assert bars[0].provider == "binance"

    def test_a_duplicate_open_time_is_refused(self) -> None:
        with pytest.raises(BinanceSnapshotError, match="duplicate"):
            self._parse([kline(1), kline(1)])

    def test_bars_outside_the_window_are_excluded_not_fatal(self) -> None:
        bars = self._parse([kline(-5), kline(0), kline(1), kline(99)])

        assert [b.open_time for b in bars] == [day(0), day(1)]

    def test_a_misaligned_open_time_is_refused(self) -> None:
        row = kline(1)
        row[0] += 3_600_000
        with pytest.raises(BinanceSnapshotError, match="not day-aligned"):
            self._parse([row])

    def test_low_above_high_is_refused(self) -> None:
        row = kline(1)
        row[2], row[3] = "5", "20"
        with pytest.raises(BinanceSnapshotError, match="exceeds high"):
            self._parse([row])

    @pytest.mark.parametrize("position", [1, 4])
    def test_open_or_close_outside_the_bar_range_is_refused(self, position: int) -> None:
        row = kline(1)
        row[position] = "999"
        with pytest.raises(BinanceSnapshotError, match="outside"):
            self._parse([row])

    @pytest.mark.parametrize("position", [5, 7])
    def test_a_negative_volume_is_refused(self, position: int) -> None:
        row = kline(1)
        row[position] = "-1"
        with pytest.raises(BinanceSnapshotError, match="non-negative"):
            self._parse([row])

    def test_a_non_finite_value_is_refused(self) -> None:
        row = kline(1)
        row[1] = "nan"
        with pytest.raises(BinanceSnapshotError, match="finite"):
            self._parse([row])

    def test_a_truncated_kline_is_refused(self) -> None:
        with pytest.raises(BinanceSnapshotError, match="at least 9 fields"):
            self._parse([[int(day(1).timestamp() * 1000), "1", "2"]])

    def test_missing_days_include_leading_and_trailing_holes(self) -> None:
        bars = self._parse([kline(1), kline(2)])

        holes = missing_days(bars, start_time=DAY0, end_time=END_TIME)
        assert holes == [day(0), day(3), day(4)]


class TestRestoredRows:
    def _record(self, **overrides: Any) -> dict[str, Any]:
        record = {
            "symbol": "BTCUSDT", "open_time": day(0).isoformat(),
            "open_time_us": int(day(0).timestamp() * 1_000_000), "open": 100.0,
            "high": 101.0, "low": 99.0, "close": 100.0, "volume": 5.0,
            "quote_volume": 500.0, "trades": 7, "provider": "binance",
            "raw_object_id": "raw_" + "a" * 64,
        }
        record.update(overrides)
        return record

    def test_a_valid_row_is_restored(self) -> None:
        assert len(bars_from_records([self._record()])) == 1

    def test_a_row_from_another_provider_is_refused(self) -> None:
        with pytest.raises(BinanceSnapshotError, match="cannot supply bars"):
            bars_from_records([self._record(provider="geckoterminal")])

    def test_an_invariant_violating_row_is_refused(self) -> None:
        with pytest.raises(BinanceSnapshotError, match="outside"):
            bars_from_records([self._record(open=999.0)])

    def test_a_misaligned_row_is_refused(self) -> None:
        with pytest.raises(BinanceSnapshotError, match="not UTC midnight"):
            bars_from_records([self._record(open_time=(day(0) + timedelta(hours=5)).isoformat())])

    def test_duplicate_identities_are_refused(self) -> None:
        with pytest.raises(BinanceSnapshotError, match="duplicate identity"):
            bars_from_records([self._record(), self._record()])

    def test_a_row_outside_declared_lineage_is_refused(self) -> None:
        with pytest.raises(BinanceSnapshotError, match="lineage does not declare"):
            bars_from_records([self._record()], allowed_raw_object_ids={"raw_" + "b" * 64})

    def test_a_missing_column_is_refused(self) -> None:
        record = self._record()
        del record["quote_volume"]
        with pytest.raises(BinanceSnapshotError, match="missing 'quote_volume'"):
            bars_from_records([record])


class TestMergeAndWatermarks:
    def _bar(self, index: int, *, symbol: str = "BTCUSDT", close: float = 100.0) -> KlineBar:
        return KlineBar(
            symbol=symbol, open_time=day(index), open=close, high=close + 1, low=close - 1,
            close=close, volume=1.0, quote_volume=10.0, trades=1, provider="binance",
            raw_object_id="raw_a",
        )

    def test_prior_rows_are_retained(self) -> None:
        merged = merge_canonical_bars([self._bar(0), self._bar(1)], [self._bar(2)])

        assert [b.open_time for b in merged] == [day(0), day(1), day(2)]

    def test_new_rows_win_on_collision(self) -> None:
        merged = merge_canonical_bars([self._bar(0, close=1.0)], [self._bar(0, close=2.0)])

        assert len(merged) == 1 and merged[0].close == 2.0

    def test_merging_is_idempotent(self) -> None:
        once = merge_canonical_bars([self._bar(0)], [self._bar(1)])
        twice = merge_canonical_bars(once, [self._bar(1)])

        assert [b.as_dict() for b in once] == [b.as_dict() for b in twice]

    def test_symbols_do_not_collide(self) -> None:
        merged = merge_canonical_bars([], [self._bar(0), self._bar(0, symbol="ETHUSDT")])

        assert len(merged) == 2

    def test_resume_starts_after_the_watermark(self) -> None:
        assert resume_start(
            {"BTCUSDT": day(2).isoformat()}, symbol="BTCUSDT", default_start=DAY0
        ) == day(3)

    def test_resume_defaults_when_unseen(self) -> None:
        assert resume_start({}, symbol="BTCUSDT", default_start=DAY0) == DAY0

    def test_a_naive_watermark_is_refused(self) -> None:
        with pytest.raises(BinanceSnapshotError, match="timezone-aware"):
            resume_start({"BTCUSDT": "2026-06-01T00:00:00"}, symbol="BTCUSDT", default_start=DAY0)

    def test_the_watermark_file_preserves_foreign_sections(self, store: Store) -> None:
        store.watermark_path.write_text(json.dumps({"other": {"a": "b"}}), encoding="utf-8")
        watermarks = WatermarkStore(store.watermark_path)

        watermarks.save({"BTCUSDT": day(0).isoformat()})

        document = json.loads(store.watermark_path.read_text(encoding="utf-8"))
        assert document["other"] == {"a": "b"}
        assert document[WatermarkStore.SECTION] == {"BTCUSDT": day(0).isoformat()}

    def test_symbol_coverage_reports_missing_days(self) -> None:
        covered, missing = symbol_covers_range(
            [self._bar(0), self._bar(3)], symbol="BTCUSDT",
            start_time=day(0), end_time=day(3),
        )

        assert not covered
        assert missing == [day(1), day(2)]


class TestBarAcquisitionStates:
    def _acquire(self, store: Store, node: MockBinance, **kwargs: Any) -> Any:
        acquirer = BinanceBarAcquirer(
            acquirer=make_acquirer(store, node), base_url="https://binance.test"
        )
        params: dict[str, Any] = {
            "symbol": "BTCUSDT", "start_time": DAY0, "end_time": END_TIME,
        }
        params.update(kwargs)
        return acquirer.acquire(**params)

    def test_complete_coverage_is_publishable(self, store: Store) -> None:
        result = self._acquire(store, MockBinance())

        assert result.state is SymbolState.PUBLISHABLE
        assert result.watermark_candidate == day(4)

    def test_an_http_failure_is_failed(self, store: Store) -> None:
        result = self._acquire(store, MockBinance(klines_status=500))

        assert result.state is SymbolState.FAILED
        assert result.watermark_candidate is None

    def test_a_transport_failure_is_failed(self, store: Store) -> None:
        result = self._acquire(store, MockBinance(klines_transport_error_for={"BTCUSDT"}))

        assert result.state is SymbolState.FAILED

    def test_an_empty_response_is_empty(self, store: Store) -> None:
        result = self._acquire(store, MockBinance(klines_by_symbol={"BTCUSDT": []}))

        assert result.state is SymbolState.EMPTY

    def test_an_invalid_payload_is_invalid(self, store: Store) -> None:
        bad = kline(0)
        bad[2], bad[3] = "5", "20"
        result = self._acquire(store, MockBinance(klines_by_symbol={"BTCUSDT": [bad]}))

        assert result.state is SymbolState.INVALID

    def test_a_gap_is_gapped_and_yields_no_watermark(self, store: Store) -> None:
        result = self._acquire(
            store, MockBinance(klines_by_symbol={"BTCUSDT": [kline(0), kline(1), kline(3)]})
        )

        assert result.state is SymbolState.GAPPED
        assert result.watermark_candidate is None

    def test_an_exhausted_window_is_already_current(self, store: Store) -> None:
        result = self._acquire(store, MockBinance(), start_time=day(9), end_time=day(4))

        assert result.state is SymbolState.ALREADY_CURRENT


# ---------------------------------------------------------------------------
# Raw lineage
# ---------------------------------------------------------------------------

class TestRawLineage:
    def test_every_response_is_preserved_byte_for_byte(self, store: Store) -> None:
        node = MockBinance()
        acquirer = make_acquirer(store, node)
        universe = BinanceUniverseAcquirer(acquirer=acquirer, base_url="https://binance.test")
        universe.fetch_exchange_info()
        universe.fetch_volume_evidence()

        served = set(node.served)
        assert acquirer.log.raw_object_ids
        for raw_id in acquirer.log.raw_object_ids:
            assert store.raw_path(raw_id).read_bytes() in served

    def test_an_error_body_is_preserved_before_raising(self, store: Store) -> None:
        node = MockBinance(exchange_info_status=500)
        acquirer = make_acquirer(store, node)
        universe = BinanceUniverseAcquirer(acquirer=acquirer, base_url="https://binance.test")

        with pytest.raises(BinanceUniverseError, match="exchangeInfo acquisition failed"):
            universe.fetch_exchange_info()

        failures = acquirer.log.failures
        assert failures[0].raw_object_id is not None
        assert store.raw_path(failures[0].raw_object_id).read_bytes() in set(node.served)

    def test_a_transport_failure_leaves_failed_acquisition_evidence(
        self, store: Store
    ) -> None:
        node = MockBinance(klines_transport_error_for={"BTCUSDT"})
        acquirer = make_acquirer(store, node)
        BinanceBarAcquirer(acquirer=acquirer, base_url="https://binance.test").acquire(
            symbol="BTCUSDT", start_time=DAY0, end_time=END_TIME
        )

        conn = sqlite3.connect(store.db)
        try:
            failed = conn.execute(
                "SELECT COUNT(*) FROM raw_acquisition WHERE status = 'FAILED'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert failed >= 1

    def test_a_rate_limited_response_is_retried(self, store: Store) -> None:
        node = MockBinance(klines_status=429)  # bar fetch only; the probe still succeeds
        slept: list[float] = []
        acquirer = make_acquirer(
            store, node, max_attempts=3, backoff_seconds=1.0, sleep=slept.append
        )
        BinanceBarAcquirer(acquirer=acquirer, base_url="https://binance.test").acquire(
            symbol="BTCUSDT", start_time=DAY0, end_time=END_TIME
        )

        assert len(acquirer.log.rate_limit_incidents) == 3
        assert slept == [1.0, 2.0]


# ---------------------------------------------------------------------------
# Runner publication
# ---------------------------------------------------------------------------

def run_runner(
    *,
    tmp_path: Path,
    store: Store,
    node: MockBinance,
    monkeypatch: pytest.MonkeyPatch,
    end_time: datetime = END_TIME,
    default_start: datetime = DAY0,
    top_n: int = 10,
    min_history_days: int = 365,
) -> tuple[int, dict[str, Any]]:
    from scripts.research import binance_universe_expansion as runner

    node.install(monkeypatch)
    report_path = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", [
        "binance_universe_expansion.py",
        "--end-time", end_time.isoformat(),
        "--default-start", default_start.isoformat(),
        "--db-path", str(store.db),
        "--raw-root", str(store.raw_root),
        "--store-root", str(store.store_root),
        "--watermark-path", str(store.watermark_path),
        "--report-path", str(report_path),
        "--top-n", str(top_n),
        "--min-history-days", str(min_history_days),
        "--base-url", "https://binance.test",
        "--code-commit", "0" * 40,
        "--max-attempts", "1",
        "--backoff-seconds", "0",
    ])
    code = runner.main()
    return code, json.loads(report_path.read_text(encoding="utf-8"))


def read_snapshot(store: Store) -> list[dict[str, Any]]:
    catalog = SqliteDatasetCatalog(store.db)
    try:
        dataset_id = catalog.resolve_latest_by_type("binance_spot_daily_bars")
    finally:
        catalog.close()
    if dataset_id is None:
        return []
    parquet = dataset_absolute_dir(store.store_root, dataset_id) / (
        "cex/binance_spot_daily_bars/bars.parquet"
    )
    return pq.read_table(parquet).to_pylist()


class TestRunnerPublication:
    def test_a_successful_run_publishes_a_resolvable_snapshot(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        code, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockBinance(), monkeypatch=monkeypatch
        )

        assert code == 0
        assert report["canonical_dataset_id"]
        assert report["catalog_reconciliation"]["state"] == "reconciled"
        assert report["snapshot_row_count"] == 20, "4 symbols x 5 days"
        assert report["live_eligible"] is False

    def test_the_report_separates_selected_excluded_and_deferred(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        node = MockBinance(symbols=DEFAULT_SYMBOLS + [
            spot_entry("BTCUPUSDT", "BTCUP"), spot_entry("USDCUSDT", "USDC"),
            spot_entry("NEWUSDT", "NEW"),
        ], first_kline_ms={"NEWUSDT": NEW_LISTING_MS})

        code, report = run_runner(
            tmp_path=tmp_path, store=store, node=node, monkeypatch=monkeypatch
        )

        assert code == 0, "a deferred symbol is documented and does not block the run"
        selected = {s["symbol"] for s in report["selected_symbols"]}
        excluded = {s["symbol"]: s["reason"] for s in report["excluded_symbols"]}
        deferred = {s["symbol"]: s["reason"] for s in report["deferred_symbols"]}

        assert {"SUPERUSDT", "JUPUSDT"} <= selected
        assert excluded["BTCUPUSDT"] == "LEVERAGED_TOKEN"
        assert excluded["USDCUSDT"] == "STABLECOIN_BASE"
        assert deferred["NEWUSDT"] == "INSUFFICIENT_HISTORY"

    def test_a_deferred_symbol_contributes_no_rows(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        node = MockBinance(
            symbols=[spot_entry("BTCUSDT", "BTC"), spot_entry("NEWUSDT", "NEW")],
            first_kline_ms={"NEWUSDT": NEW_LISTING_MS},
        )

        code, report = run_runner(
            tmp_path=tmp_path, store=store, node=node, monkeypatch=monkeypatch
        )

        assert code == 0
        assert {r["symbol"] for r in read_snapshot(store)} == {"BTCUSDT"}
        assert report["symbols_by_state"]["DEFERRED"][0]["symbol"] == "NEWUSDT"

    def test_watermarks_advance_only_after_publication(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockBinance(), monkeypatch=monkeypatch
        )

        assert report["watermarks_before"] == {}
        assert report["watermarks_after"]["BTCUSDT"] == day(4).isoformat()
        assert WatermarkStore(store.watermark_path).load()["BTCUSDT"] == day(4).isoformat()

    @pytest.mark.parametrize(
        "node_kwargs",
        [
            {"klines_status_by_symbol": {"BTCUSDT": 500}},
            {"klines_transport_error_for": {"BTCUSDT"}},
            {"klines_by_symbol": {"BTCUSDT": []}},
            {"klines_by_symbol": {"BTCUSDT": [kline(0), kline(1), kline(3), kline(4)]}},
        ],
    )
    def test_one_failing_symbol_blocks_the_whole_publication(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch,
        node_kwargs: dict[str, Any],
    ) -> None:
        """The other three symbols are clean and would otherwise publish."""
        code, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockBinance(**node_kwargs),
            monkeypatch=monkeypatch,
        )

        assert code == 1
        assert report["canonical_dataset_id"] is None
        assert [b["symbol"] for b in report["blocking_symbols"]] == ["BTCUSDT"]
        assert read_snapshot(store) == []
        assert WatermarkStore(store.watermark_path).load() == {}

    def test_a_failed_run_retains_prior_canonical_data_and_watermarks(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_runner(tmp_path=tmp_path, store=store, node=MockBinance(), monkeypatch=monkeypatch)
        before = read_snapshot(store)
        watermarks_before = WatermarkStore(store.watermark_path).load()

        code, report = run_runner(
            tmp_path=tmp_path, store=store, monkeypatch=monkeypatch,
            node=MockBinance(klines_status=500), end_time=day(9),
        )

        assert code == 1
        assert report["canonical_dataset_id"] is None
        assert read_snapshot(store) == before
        assert WatermarkStore(store.watermark_path).load() == watermarks_before

    def test_an_incremental_run_publishes_the_full_snapshot(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_runner(
            tmp_path=tmp_path, store=store, monkeypatch=monkeypatch, end_time=day(2),
            node=MockBinance(klines_by_symbol={
                s["symbol"]: [kline(i) for i in range(3)] for s in DEFAULT_SYMBOLS
            }),
        )
        assert len(read_snapshot(store)) == 12

        code, report = run_runner(
            tmp_path=tmp_path, store=store, monkeypatch=monkeypatch, end_time=day(4),
            node=MockBinance(klines_by_symbol={
                s["symbol"]: [kline(3), kline(4)] for s in DEFAULT_SYMBOLS
            }),
        )

        assert code == 0
        assert report["snapshot_row_count"] == 20, "a delta must not replace history"
        assert report["prior_dataset_reconciliation"]["state"] == "reconciled"

    def test_three_consecutive_refreshes_keep_lineage_closed(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for index in range(3):
            code, _ = run_runner(
                tmp_path=tmp_path, store=store, monkeypatch=monkeypatch, end_time=day(index),
                node=MockBinance(klines_by_symbol={
                    s["symbol"]: [kline(index)] for s in DEFAULT_SYMBOLS
                }),
            )
            assert code == 0, f"refresh {index} failed"

        rows = read_snapshot(store)
        catalog = SqliteDatasetCatalog(store.db)
        try:
            dataset_id = str(catalog.resolve_latest_by_type("binance_spot_daily_bars"))
            declared = {str(r["raw_object_id"]) for r in catalog.list_raw_inputs(dataset_id)}
        finally:
            catalog.close()

        assert len(rows) == 12
        assert {r["raw_object_id"] for r in rows} <= declared

    def test_the_report_records_lineage_and_rate_limits(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockBinance(), monkeypatch=monkeypatch
        )

        assert report["raw_dependency_count"] >= 3
        assert report["snapshot_raw_object_count"] >= 1
        assert report["failed_acquisition_count"] == 0
        assert report["rate_limit_incidents"] == []
        assert report["exclusion_taxonomy_version"] == EXCLUSION_TAXONOMY_VERSION
        assert report["volume_window"] == "24h"
        assert report["snapshot_span"]["start"] == day(0).isoformat()

    def test_the_run_uses_a_real_commit_and_config_hash(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_runner(tmp_path=tmp_path, store=store, node=MockBinance(), monkeypatch=monkeypatch)

        catalog = SqliteDatasetCatalog(store.db)
        try:
            dataset_id = str(catalog.resolve_latest_by_type("binance_spot_daily_bars"))
            row = catalog.get_dataset(dataset_id)
        finally:
            catalog.close()

        assert row is not None
        assert row["code_commit"] == "0" * 40
        assert len(row["config_sha256"]) == 64
