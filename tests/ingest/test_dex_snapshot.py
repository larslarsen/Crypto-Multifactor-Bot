"""DEX-002 — tests for screened DEX OHLCV acquisition and canonical snapshot.

Every test drives the shipped implementation: `dex_providers`, `dex_snapshot`, and
the runner `scripts/research/dex002_snapshot.py`. Publication is proven by running
the runner, not by reimplementing it here.

No test may reach the network: every HTTP path goes through an injected
`MockTransport`, and `forbid_real_network` fails any attempt to build a bare client.
"""

from __future__ import annotations

import hashlib
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

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations
from cryptofactors.ingest import dex_providers
from cryptofactors.ingest.dex_providers import (
    DEFILLAMA_PROVIDER,
    DEXSCREENER_PROVIDER,
    GECKOTERMINAL_PROVIDER,
    AcquisitionLog,
    DefiLlamaContextProvider,
    DexScreenerScreeningProvider,
    ProviderCapability,
    RawHttpAcquirer,
    ScreeningObservation,
    ScreeningStatus,
    ScreeningThresholds,
    decide_screening,
    evaluate_metrics,
)
from cryptofactors.ingest.dex_snapshot import (
    DexSnapshotEngine,
    chain_family,
    DexSnapshotError,
    GeckoTerminalOhlcvSource,
    OhlcvBar,
    PoolIdentity,
    WatermarkStore,
    canonical_pool_address,
    contiguous_prefix_end,
    find_interval_gaps,
    merge_canonical_bars,
    parse_geckoterminal_bars,
    resume_start,
    watermark_key,
)
from cryptofactors.ingest.raw.catalog import SqliteRawObjectCatalog
from cryptofactors.ingest.raw.models import RawObjectStoreConfig
from cryptofactors.ingest.raw.paths import content_addressed_absolute_path
from cryptofactors.ingest.raw.writer import RawObjectWriter

# Captured before any patching. Re-reading httpx.Client at patch time would chain
# each new patch through the previous one, so the first node installed would keep
# serving every later request.
REAL_HTTPX_CLIENT = httpx.Client

CHAIN = "arbitrum"
POOL = "0xbe3ad6a5669dc0b8b12febc03608860c31e2eef6"
POOL_B = "0x1111111111111111111111111111111111111111"
SOLANA_POOL = "7xKXtg2CW87dEnBhr1zDLcC1e2y5s9kVfCLwSSPWSDbM"

DAY0 = datetime(2026, 6, 1, tzinfo=UTC)
END_TIME = DAY0 + timedelta(days=4)


def day(index: int) -> datetime:
    return DAY0 + timedelta(days=index)


def bar_row(index: int, *, close: float = 100.0, volume: float = 5.0) -> list[Any]:
    return [int(day(index).timestamp()), close, close + 1.0, close - 1.0, close, volume]


@pytest.fixture(autouse=True)
def forbid_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test in this module may contact a public endpoint."""
    def guarded(*args: Any, **kwargs: Any) -> httpx.Client:
        if kwargs.get("transport") is None:
            raise AssertionError("a real network client was requested; use the mock transport")
        return REAL_HTTPX_CLIENT(*args, **kwargs)

    monkeypatch.setattr(dex_providers.httpx, "Client", guarded)


class MockDexNode:
    """Serves DexScreener, DefiLlama and GeckoTerminal from in-memory fixtures."""

    def __init__(
        self,
        *,
        liquidity: float | None = 250_000.0,
        volume_24h: float | None = 90_000.0,
        bars: list[list[Any]] | None = None,
        screening_status: int = 200,
        ohlcv_status: int = 200,
        screening_transport_error: bool = False,
        ohlcv_transport_error: bool = False,
        screening_body: bytes | None = None,
        pairs_override: Any = None,
        bars_by_pool: dict[str, list[list[Any]]] | None = None,
    ) -> None:
        self.bars_by_pool = bars_by_pool or {}
        self.liquidity = liquidity
        self.volume_24h = volume_24h
        self.bars = bars if bars is not None else [bar_row(i) for i in range(5)]
        self.screening_status = screening_status
        self.ohlcv_status = ohlcv_status
        self.screening_transport_error = screening_transport_error
        self.ohlcv_transport_error = ohlcv_transport_error
        self.screening_body = screening_body
        self.pairs_override = pairs_override
        self.requests: list[str] = []
        self.served: list[bytes] = []

    def _respond(self, status: int, payload: Any) -> httpx.Response:
        body = json.dumps(payload).encode()
        self.served.append(body)
        return httpx.Response(status, content=body, headers={"content-type": "application/json"})

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)

        if "dexscreener" in url:
            if self.screening_transport_error:
                raise httpx.ConnectError("screening refused", request=request)
            if self.screening_body is not None:
                self.served.append(self.screening_body)
                return httpx.Response(self.screening_status, content=self.screening_body)
            if self.screening_status != 200:
                return self._respond(self.screening_status, {"error": "unavailable"})
            if self.pairs_override is not None:
                return self._respond(200, {"pairs": self.pairs_override})
            pair: dict[str, Any] = {}
            if self.liquidity is not None:
                pair["liquidity"] = {"usd": self.liquidity}
            if self.volume_24h is not None:
                pair["volume"] = {"h24": self.volume_24h}
            return self._respond(200, {"pairs": [pair]})

        if "llama" in url:
            return self._respond(200, {"coins": {"arbitrum:0xabc": {"price": 1.0}}})

        if "geckoterminal" in url:
            if self.ohlcv_transport_error:
                raise httpx.ConnectError("ohlcv refused", request=request)
            if self.ohlcv_status != 200:
                return self._respond(self.ohlcv_status, {"error": "unavailable"})
            rows = next(
                (v for k, v in self.bars_by_pool.items() if k.lower() in url.lower()),
                self.bars,
            )
            return self._respond(200, {"data": {"attributes": {"ohlcv_list": list(rows)}}})

        return self._respond(404, {"error": "unknown"})

    def client(self) -> httpx.Client:
        return REAL_HTTPX_CLIENT(transport=httpx.MockTransport(self.handler))

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            dex_providers.httpx, "Client",
            lambda **_kw: REAL_HTTPX_CLIENT(transport=httpx.MockTransport(self.handler)),
        )


class Store:
    """Raw object store plus the control database."""

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

    def acquisitions(self) -> list[dict[str, Any]]:
        conn = sqlite3.connect(self.db)
        try:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute("SELECT * FROM raw_acquisition")]
        finally:
            conn.close()


@pytest.fixture
def store(tmp_path: Path) -> Iterator[Store]:
    created = Store(tmp_path)
    yield created
    created.close()


def make_engine(store: Store, node: MockDexNode, **kwargs: Any) -> DexSnapshotEngine:
    acquirer = RawHttpAcquirer(
        raw_writer=store.writer, client=node.client(), log=AcquisitionLog()
    )
    return DexSnapshotEngine(
        acquirer=acquirer,
        screening_providers=[DexScreenerScreeningProvider(), DefiLlamaContextProvider()],
        **kwargs,
    )


def identity() -> PoolIdentity:
    return PoolIdentity.create(CHAIN, POOL)


# ---------------------------------------------------------------------------
# Provider capability separation
# ---------------------------------------------------------------------------

class TestProviderCapabilities:
    def test_each_provider_declares_only_its_evidenced_capability(self) -> None:
        assert DexScreenerScreeningProvider.capability is ProviderCapability.AUTHORITATIVE_SCREENING
        assert DefiLlamaContextProvider.capability is ProviderCapability.CONTEXT
        assert GeckoTerminalOhlcvSource.capability is ProviderCapability.INTERVAL_OHLCV

    def test_dexscreener_cannot_emit_ohlcv_rows(self) -> None:
        """Structural, not behavioural: the screening provider has no bar-producing API."""
        provider = DexScreenerScreeningProvider()

        assert not hasattr(provider, "fetch")
        assert not hasattr(provider, "fetch_pool_ohlcv")
        assert provider.capability is not ProviderCapability.INTERVAL_OHLCV

    def test_defillama_cannot_emit_ohlcv_rows(self) -> None:
        provider = DefiLlamaContextProvider()

        assert not hasattr(provider, "fetch")
        assert not hasattr(provider, "fetch_pool_ohlcv")

    def test_only_geckoterminal_produces_bars(self, store: Store) -> None:
        node = MockDexNode()
        engine = make_engine(store, node)

        acquisition = engine.acquire_pool(
            identity=identity(), watermarks={}, default_start=DAY0, end_time=END_TIME
        )

        assert acquisition.bars
        assert {bar.provider for bar in acquisition.bars} == {GECKOTERMINAL_PROVIDER}


# ---------------------------------------------------------------------------
# Screening
# ---------------------------------------------------------------------------

class TestScreening:
    def test_an_authoritative_observation_passes_on_both_thresholds(self) -> None:
        thresholds = ScreeningThresholds()
        observation = evaluate_metrics(
            provider=DEXSCREENER_PROVIDER, observed_at=DAY0,
            liquidity_usd=50_000.0, volume_24h_usd=10_000.0,
            thresholds=thresholds, raw_object_id="raw_a", acquisition_id="acq_a",
        )

        assert observation.status is ScreeningStatus.PASS
        assert observation.liquidity_usd == 50_000.0
        assert observation.volume_24h_usd == 10_000.0

    @pytest.mark.parametrize(
        ("liquidity", "volume"),
        [(49_999.99, 10_000.0), (50_000.0, 9_999.99), (0.0, 0.0)],
    )
    def test_a_valid_below_threshold_observation_rejects(
        self, liquidity: float, volume: float
    ) -> None:
        observation = evaluate_metrics(
            provider=DEXSCREENER_PROVIDER, observed_at=DAY0,
            liquidity_usd=liquidity, volume_24h_usd=volume,
            thresholds=ScreeningThresholds(), raw_object_id=None, acquisition_id=None,
        )

        assert observation.status is ScreeningStatus.REJECT

    @pytest.mark.parametrize("missing", ["liquidity", "volume", "both"])
    def test_missing_metrics_are_unavailable_not_reject(self, missing: str) -> None:
        """An unobserved pool is retryable; it is not evidence of death."""
        observation = evaluate_metrics(
            provider=DEXSCREENER_PROVIDER, observed_at=DAY0,
            liquidity_usd=None if missing in ("liquidity", "both") else 100_000.0,
            volume_24h_usd=None if missing in ("volume", "both") else 50_000.0,
            thresholds=ScreeningThresholds(), raw_object_id=None, acquisition_id=None,
        )

        assert observation.status is ScreeningStatus.UNAVAILABLE

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), "abc", None, True])
    def test_non_finite_metrics_cannot_pass(self, value: Any) -> None:
        observation = evaluate_metrics(
            provider=DEXSCREENER_PROVIDER, observed_at=DAY0,
            liquidity_usd=value, volume_24h_usd=99_999.0,
            thresholds=ScreeningThresholds(), raw_object_id=None, acquisition_id=None,
        )

        assert observation.status is ScreeningStatus.UNAVAILABLE

    def test_context_only_evidence_cannot_pass_a_pool(self) -> None:
        """DefiLlama admitting pools was the prior fail-open defect."""
        context = ScreeningObservation(
            provider=DEFILLAMA_PROVIDER, capability=ProviderCapability.CONTEXT,
            observed_at=DAY0, liquidity_usd=10_000_000.0, volume_24h_usd=10_000_000.0,
            status=ScreeningStatus.CONTEXT_ONLY, reason="context",
        )

        decision = decide_screening(
            chain=CHAIN, pool_address=POOL, observations=[context],
            thresholds=ScreeningThresholds(),
        )

        assert decision.status is ScreeningStatus.UNAVAILABLE
        assert not decision.passed

    def test_no_observations_at_all_is_unavailable(self) -> None:
        decision = decide_screening(
            chain=CHAIN, pool_address=POOL, observations=[], thresholds=ScreeningThresholds()
        )

        assert decision.status is ScreeningStatus.UNAVAILABLE

    def test_a_provider_error_is_unavailable_and_retryable(self, store: Store) -> None:
        node = MockDexNode(screening_status=503)
        engine = make_engine(store, node)

        decision = engine.screen(identity())

        assert decision.status is ScreeningStatus.UNAVAILABLE
        assert not decision.passed

    def test_a_transport_failure_is_unavailable(self, store: Store) -> None:
        node = MockDexNode(screening_transport_error=True)
        engine = make_engine(store, node)

        decision = engine.screen(identity())

        assert decision.status is ScreeningStatus.UNAVAILABLE

    def test_every_configured_provider_is_called_for_context(self, store: Store) -> None:
        node = MockDexNode()
        engine = make_engine(store, node)

        decision = engine.screen(identity())

        providers = {obs.provider for obs in decision.observations}
        assert providers == {DEXSCREENER_PROVIDER, DEFILLAMA_PROVIDER}
        assert decision.status is ScreeningStatus.PASS

    def test_thresholds_are_configurable_and_fingerprinted(self) -> None:
        default = ScreeningThresholds()
        custom = ScreeningThresholds(min_liquidity_usd=1.0, min_volume_24h_usd=2.0)

        assert default.as_dict() == {"min_liquidity_usd": 50_000.0, "min_volume_24h_usd": 10_000.0}
        assert custom.fingerprint() != default.fingerprint()
        assert custom.fingerprint() == ScreeningThresholds(1.0, 2.0).fingerprint()

    def test_a_screened_out_pool_acquires_no_bars(self, store: Store) -> None:
        node = MockDexNode(liquidity=1.0, volume_24h=1.0)
        engine = make_engine(store, node)

        acquisition = engine.acquire_pool(
            identity=identity(), watermarks={}, default_start=DAY0, end_time=END_TIME
        )

        assert acquisition.bars == ()
        assert acquisition.decision.status is ScreeningStatus.REJECT
        assert not any("geckoterminal" in url for url in node.requests)


# ---------------------------------------------------------------------------
# Genuine bars only
# ---------------------------------------------------------------------------

class TestBarValidation:
    def _parse(self, rows: list[list[Any]], **kwargs: Any) -> list[OhlcvBar]:
        payload = {"data": {"attributes": {"ohlcv_list": rows}}}
        params: dict[str, Any] = {
            "identity": identity(), "start_time": DAY0, "end_time": END_TIME,
            "raw_object_id": "raw_x",
        }
        params.update(kwargs)
        return parse_geckoterminal_bars(payload, **params)

    def test_valid_bars_decode_in_deterministic_order(self) -> None:
        bars = self._parse([bar_row(2), bar_row(0), bar_row(1)])

        assert [b.timestamp for b in bars] == [day(0), day(1), day(2)]
        assert all(b.provider == GECKOTERMINAL_PROVIDER for b in bars)

    def test_a_duplicate_timestamp_is_refused(self) -> None:
        with pytest.raises(DexSnapshotError, match="duplicate bar timestamp"):
            self._parse([bar_row(1), bar_row(1)])

    def test_bars_outside_the_requested_range_are_excluded_not_published(self) -> None:
        """Pagination returns extra history; it must never reach the snapshot."""
        bars = self._parse([bar_row(-5), bar_row(0), bar_row(1), bar_row(99)])

        assert [b.timestamp for b in bars] == [day(0), day(1)]

    def test_a_response_entirely_outside_the_range_yields_no_bars(self) -> None:
        assert self._parse([bar_row(-9), bar_row(-8)]) == []

    def test_a_misaligned_timestamp_is_refused(self) -> None:
        row = bar_row(1)
        row[0] += 3_600
        with pytest.raises(DexSnapshotError, match="not aligned"):
            self._parse([row])

    @pytest.mark.parametrize("index", [1, 2, 3, 4, 5])
    def test_a_non_finite_value_is_refused(self, index: int) -> None:
        row = bar_row(1)
        row[index] = float("nan")
        with pytest.raises(DexSnapshotError, match="finite"):
            self._parse([row])

    def test_a_negative_volume_is_refused(self) -> None:
        row = bar_row(1)
        row[5] = -1.0
        with pytest.raises(DexSnapshotError, match="non-negative"):
            self._parse([row])

    def test_low_above_high_is_refused(self) -> None:
        # [ts, open, high, low, close, volume]
        with pytest.raises(DexSnapshotError, match="exceeds high"):
            self._parse([[int(day(1).timestamp()), 10.0, 5.0, 20.0, 10.0, 1.0]])

    @pytest.mark.parametrize(("field", "position"), [("open", 1), ("close", 4)])
    def test_open_or_close_outside_the_bar_range_is_refused(
        self, field: str, position: int
    ) -> None:
        row = [int(day(1).timestamp()), 10.0, 12.0, 8.0, 10.0, 1.0]
        row[position] = 99.0
        with pytest.raises(DexSnapshotError, match=field):
            self._parse([row])

    def test_a_truncated_item_is_refused(self) -> None:
        with pytest.raises(DexSnapshotError, match="at least 6 fields"):
            self._parse([[int(day(1).timestamp()), 1.0, 2.0]])

    def test_a_non_list_payload_is_refused(self) -> None:
        with pytest.raises(DexSnapshotError, match="ohlcv_list must be a list"):
            parse_geckoterminal_bars(
                {"data": {"attributes": {"ohlcv_list": {}}}},
                identity=identity(), start_time=DAY0, end_time=END_TIME, raw_object_id="raw_x",
            )

    def test_a_missing_attributes_block_is_refused(self) -> None:
        with pytest.raises(DexSnapshotError, match="no data.attributes"):
            parse_geckoterminal_bars(
                {"data": {}}, identity=identity(), start_time=DAY0, end_time=END_TIME,
                raw_object_id="raw_x",
            )

    def test_gaps_are_detected_and_never_filled(self) -> None:
        bars = self._parse([bar_row(0), bar_row(1), bar_row(3)])
        gaps = find_interval_gaps(bars)

        assert len(bars) == 3, "no synthetic bar was inserted"
        assert gaps == [(day(1), day(3))]

    def test_contiguous_prefix_stops_at_the_first_gap(self) -> None:
        bars = self._parse([bar_row(0), bar_row(1), bar_row(3), bar_row(4)])

        assert contiguous_prefix_end(bars) == day(1)

    def test_contiguous_prefix_of_a_complete_run_is_the_last_bar(self) -> None:
        bars = self._parse([bar_row(i) for i in range(4)])

        assert contiguous_prefix_end(bars) == day(3)


# ---------------------------------------------------------------------------
# Pool identity
# ---------------------------------------------------------------------------

class TestPoolIdentity:
    def test_evm_addresses_are_lowercased(self) -> None:
        assert canonical_pool_address(POOL.upper().replace("0X", "0x"), chain=CHAIN) == POOL

    def test_non_evm_addresses_preserve_case(self) -> None:
        """Solana base58 is case-sensitive; lowercasing would merge distinct pools."""
        assert canonical_pool_address(SOLANA_POOL, chain="solana") == SOLANA_POOL

    def test_a_malformed_evm_address_fails_closed(self) -> None:
        """It must not fall through and be accepted as a non-EVM identity."""
        with pytest.raises(DexSnapshotError, match="not a valid 20-byte EVM address"):
            canonical_pool_address("0xdeadbeef", chain=CHAIN)

    @pytest.mark.parametrize(
        "bad", ["0x" + "g" * 40, "0x" + "a" * 39, "0x" + "a" * 41, "not-an-address"]
    )
    def test_every_malformed_evm_address_is_refused(self, bad: str) -> None:
        with pytest.raises(DexSnapshotError, match="not a valid 20-byte EVM address"):
            canonical_pool_address(bad, chain=CHAIN)

    def test_an_evm_address_on_a_solana_chain_is_refused(self) -> None:
        with pytest.raises(DexSnapshotError, match="not a valid base58 address"):
            canonical_pool_address("0x" + "a" * 40, chain="solana")

    def test_an_unregistered_chain_is_refused(self) -> None:
        """An unknown chain means an unvalidated address grammar; fail closed."""
        with pytest.raises(DexSnapshotError, match="no registered address family"):
            canonical_pool_address(POOL, chain="fantasychain")

    def test_chain_families_are_declared(self) -> None:
        assert chain_family("arbitrum") == "evm"
        assert chain_family("solana") == "solana"

    def test_the_same_address_on_two_chains_does_not_collide(self) -> None:
        arbitrum = PoolIdentity.create("arbitrum", POOL)
        base = PoolIdentity.create("base", POOL)

        assert arbitrum != base
        assert arbitrum.key != base.key

    def test_chain_is_part_of_the_dedupe_key(self) -> None:
        left = OhlcvBar(
            chain="arbitrum", pool_address=POOL, timestamp=day(0), open=1.0, high=1.0,
            low=1.0, close=1.0, volume=1.0, provider=GECKOTERMINAL_PROVIDER, raw_object_id="raw_a",
        )
        right = OhlcvBar(
            chain="base", pool_address=POOL, timestamp=day(0), open=2.0, high=2.0,
            low=2.0, close=2.0, volume=2.0, provider=GECKOTERMINAL_PROVIDER, raw_object_id="raw_b",
        )

        assert left.dedupe_key != right.dedupe_key
        assert len(merge_canonical_bars([], [left, right])) == 2

    def test_chain_is_part_of_the_watermark_key(self) -> None:
        arbitrum = watermark_key(provider="geckoterminal", identity=PoolIdentity.create("arbitrum", POOL))
        base = watermark_key(provider="geckoterminal", identity=PoolIdentity.create("base", POOL))

        assert arbitrum != base

    @pytest.mark.parametrize("bad", ["", "   "])
    def test_an_empty_address_is_refused(self, bad: str) -> None:
        with pytest.raises(DexSnapshotError):
            canonical_pool_address(bad, chain=CHAIN)


# ---------------------------------------------------------------------------
# Raw lineage
# ---------------------------------------------------------------------------

class TestRawLineage:
    def test_every_controlling_response_is_preserved_byte_for_byte(
        self, store: Store
    ) -> None:
        node = MockDexNode()
        engine = make_engine(store, node)
        engine.acquire_pool(
            identity=identity(), watermarks={}, default_start=DAY0, end_time=END_TIME
        )

        served = set(node.served)
        raw_ids = engine.log.raw_object_ids
        assert raw_ids

        for raw_id in raw_ids:
            body = store.raw_path(raw_id).read_bytes()
            assert body in served
            assert f"raw_{hashlib.sha256(body).hexdigest()}" == raw_id

    def test_screening_and_ohlcv_are_both_preserved(self, store: Store) -> None:
        node = MockDexNode()
        engine = make_engine(store, node)
        engine.acquire_pool(
            identity=identity(), watermarks={}, default_start=DAY0, end_time=END_TIME
        )

        providers = {o.provider for o in engine.log.outcomes if o.raw_object_id}
        assert providers == {DEXSCREENER_PROVIDER, DEFILLAMA_PROVIDER, GECKOTERMINAL_PROVIDER}

    def test_an_http_error_body_is_preserved_before_raising(self, store: Store) -> None:
        node = MockDexNode(ohlcv_status=500)
        engine = make_engine(store, node)

        acquisition = engine.acquire_pool(
            identity=identity(), watermarks={}, default_start=DAY0, end_time=END_TIME
        )

        failures = engine.log.failures
        assert [f.failure_kind for f in failures] == ["http_status"]
        assert failures[0].raw_object_id is not None
        assert store.raw_path(failures[0].raw_object_id).read_bytes() in set(node.served)
        assert acquisition.error is not None

    def test_an_invalid_json_body_is_preserved_and_reported(self, store: Store) -> None:
        node = MockDexNode(screening_body=b"<html>gateway</html>")
        engine = make_engine(store, node)

        engine.screen(identity())

        failures = engine.log.failures
        assert [f.failure_kind for f in failures] == ["invalid_json"]
        assert failures[0].raw_object_id is not None

    def test_a_transport_failure_leaves_failed_acquisition_evidence(
        self, store: Store
    ) -> None:
        node = MockDexNode(screening_transport_error=True)
        engine = make_engine(store, node)

        engine.screen(identity())

        failures = engine.log.failures
        assert failures[0].failure_kind == "transport"
        assert failures[0].raw_object_id is None, "no body was received"
        recorded = [a for a in store.acquisitions() if a["status"] == "FAILED"]
        assert recorded, "a failed acquisition row must exist"

    def test_every_bar_names_the_response_it_came_from(self, store: Store) -> None:
        node = MockDexNode()
        engine = make_engine(store, node)

        acquisition = engine.acquire_pool(
            identity=identity(), watermarks={}, default_start=DAY0, end_time=END_TIME
        )

        raw_ids = {bar.raw_object_id for bar in acquisition.bars}
        assert len(raw_ids) == 1
        assert raw_ids <= engine.log.raw_object_ids


# ---------------------------------------------------------------------------
# Merge and watermarks
# ---------------------------------------------------------------------------

class TestMergeAndWatermarks:
    def _bar(self, index: int, *, close: float = 100.0, chain: str = CHAIN) -> OhlcvBar:
        return OhlcvBar(
            chain=chain, pool_address=POOL, timestamp=day(index), open=close, high=close + 1,
            low=close - 1, close=close, volume=1.0, provider=GECKOTERMINAL_PROVIDER,
            raw_object_id="raw_a",
        )

    def test_a_primary_only_merge_returns_the_acquired_rows(self) -> None:
        acquired = [self._bar(1), self._bar(0)]

        merged = merge_canonical_bars([], acquired)

        assert [b.timestamp for b in merged] == [day(0), day(1)]

    def test_prior_rows_are_retained_alongside_new_rows(self) -> None:
        """A delta must never replace history."""
        prior = [self._bar(0), self._bar(1)]
        acquired = [self._bar(2), self._bar(3)]

        merged = merge_canonical_bars(prior, acquired)

        assert [b.timestamp for b in merged] == [day(i) for i in range(4)]

    def test_dedupe_is_deterministic_and_prefers_newly_acquired(self) -> None:
        prior = [self._bar(0, close=1.0)]
        acquired = [self._bar(0, close=2.0)]

        merged = merge_canonical_bars(prior, acquired)

        assert len(merged) == 1
        assert merged[0].close == 2.0

    def test_merging_is_idempotent(self) -> None:
        prior = [self._bar(0), self._bar(1)]
        acquired = [self._bar(1), self._bar(2)]

        once = merge_canonical_bars(prior, acquired)
        twice = merge_canonical_bars(once, acquired)

        assert [b.as_dict() for b in once] == [b.as_dict() for b in twice]

    def test_resume_starts_at_the_default_when_unseen(self) -> None:
        assert resume_start(
            {}, provider="geckoterminal", identity=identity(), default_start=DAY0
        ) == DAY0

    def test_resume_starts_after_the_recorded_watermark(self) -> None:
        key = watermark_key(provider="geckoterminal", identity=identity())

        start = resume_start(
            {key: day(2).isoformat()}, provider="geckoterminal", identity=identity(),
            default_start=DAY0,
        )

        assert start == day(3)

    def test_a_naive_watermark_is_refused(self) -> None:
        key = watermark_key(provider="geckoterminal", identity=identity())
        with pytest.raises(DexSnapshotError, match="timezone-aware"):
            resume_start(
                {key: "2026-06-01T00:00:00"}, provider="geckoterminal",
                identity=identity(), default_start=DAY0,
            )

    def test_the_watermark_candidate_stops_at_the_first_gap(self, store: Store) -> None:
        node = MockDexNode(bars=[bar_row(0), bar_row(1), bar_row(3)])
        engine = make_engine(store, node)

        acquisition = engine.acquire_pool(
            identity=identity(), watermarks={}, default_start=DAY0, end_time=END_TIME
        )

        assert acquisition.gaps == ((day(1), day(3)),)
        assert acquisition.watermark_candidate is None, "a gap yields no watermark at all"
        assert not acquisition.usable

    @pytest.mark.parametrize(
        "node_kwargs",
        [{"bars": []}, {"ohlcv_status": 500}, {"ohlcv_transport_error": True}],
    )
    def test_an_empty_or_failed_result_offers_no_watermark(
        self, store: Store, node_kwargs: dict[str, Any]
    ) -> None:
        node = MockDexNode(**node_kwargs)
        engine = make_engine(store, node)

        acquisition = engine.acquire_pool(
            identity=identity(), watermarks={}, default_start=DAY0, end_time=END_TIME
        )

        assert acquisition.watermark_candidate is None
        assert acquisition.error is not None

    def test_a_screening_failure_offers_no_watermark(self, store: Store) -> None:
        node = MockDexNode(screening_status=503)
        engine = make_engine(store, node)

        acquisition = engine.acquire_pool(
            identity=identity(), watermarks={}, default_start=DAY0, end_time=END_TIME
        )

        assert acquisition.watermark_candidate is None

    def test_the_watermark_store_retains_unrelated_shards(self, store: Store) -> None:
        watermarks = WatermarkStore(store.watermark_path)
        watermarks.save({"geckoterminal:base:0xother": day(0).isoformat()})

        loaded = watermarks.load()
        loaded[watermark_key(provider="geckoterminal", identity=identity())] = day(1).isoformat()
        watermarks.save(loaded)

        assert set(watermarks.load()) == {
            "geckoterminal:base:0xother",
            watermark_key(provider="geckoterminal", identity=identity()),
        }

    def test_the_watermark_file_preserves_foreign_sections(self, store: Store) -> None:
        store.watermark_path.write_text(json.dumps({"other_job": {"a": "b"}}), encoding="utf-8")
        watermarks = WatermarkStore(store.watermark_path)

        watermarks.save({"geckoterminal:arbitrum:0xpool": day(0).isoformat()})

        document = json.loads(store.watermark_path.read_text(encoding="utf-8"))
        assert document["other_job"] == {"a": "b"}
        assert WatermarkStore.SECTION in document


# ---------------------------------------------------------------------------
# Runner publication
# ---------------------------------------------------------------------------

def write_pools(tmp_path: Path, pools: list[dict[str, str]]) -> Path:
    path = tmp_path / "pools.json"
    path.write_text(json.dumps({"pools": pools}), encoding="utf-8")
    return path


def run_runner(
    *,
    tmp_path: Path,
    store: Store,
    node: MockDexNode,
    monkeypatch: pytest.MonkeyPatch,
    pools: list[dict[str, str]] | None = None,
    end_time: datetime = END_TIME,
    max_attempts: int = 1,
) -> tuple[int, dict[str, Any]]:
    from scripts.research import dex002_snapshot as runner

    node.install(monkeypatch)
    report_path = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", [
        "dex002_snapshot.py",
        "--pools", str(write_pools(tmp_path, pools or [{"chain": CHAIN, "pool_address": POOL}])),
        "--end-time", end_time.isoformat(),
        "--default-start", DAY0.isoformat(),
        "--db-path", str(store.db),
        "--raw-root", str(store.raw_root),
        "--store-root", str(store.store_root),
        "--watermark-path", str(store.watermark_path),
        "--report-path", str(report_path),
        "--code-commit", "0" * 40,
        # Retry/backoff is exercised directly in TestRetryAndRateLimits; runner tests
        # must not spend real seconds sleeping on deliberate failures.
        "--max-attempts", str(max_attempts),
        "--backoff-seconds", "0",
    ])
    code = runner.main()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return code, report


class TestRunnerPublication:
    def test_a_successful_run_publishes_a_resolvable_snapshot(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        code, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch
        )

        assert code == 0
        catalog = SqliteDatasetCatalog(store.db)
        try:
            dataset_id = catalog.resolve_latest_by_type("dex_pool_ohlcv_daily")
            assert dataset_id is not None
            assert report["published_dataset_id"] == dataset_id

            raw_inputs = {r["raw_object_id"] for r in catalog.list_raw_inputs(dataset_id)}
            assert raw_inputs, "controlling responses must be declared"
            files = catalog.list_files(dataset_id)
            assert len(files) == 1
            assert files[0]["row_count"] == report["snapshot_row_count"] == 5
        finally:
            catalog.close()

    def test_the_published_rows_are_genuine_bars(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_runner(tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch)

        records = read_snapshot(store)
        assert {r["provider"] for r in records} == {GECKOTERMINAL_PROVIDER}
        assert [r["timestamp"] for r in records] == [day(i).isoformat() for i in range(5)]
        for record in records:
            assert record["low"] <= record["open"] <= record["high"]
            assert record["raw_object_id"].startswith("raw_")

    def test_watermarks_advance_only_after_publication(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch
        )

        key = watermark_key(provider="geckoterminal", identity=identity())
        assert report["watermarks_before"] == {}
        assert report["watermarks_after"][key] == day(4).isoformat()
        assert WatermarkStore(store.watermark_path).load()[key] == day(4).isoformat()

    def test_an_incremental_run_publishes_the_full_snapshot(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The second run acquires only new days but must republish the union."""
        run_runner(
            tmp_path=tmp_path, store=store, monkeypatch=monkeypatch,
            node=MockDexNode(bars=[bar_row(i) for i in range(3)]),
            end_time=day(2),
        )
        first = read_snapshot(store)
        assert len(first) == 3

        code, report = run_runner(
            tmp_path=tmp_path, store=store, monkeypatch=monkeypatch,
            node=MockDexNode(bars=[bar_row(3), bar_row(4)]),
            end_time=day(4),
        )

        assert code == 0
        assert report["snapshot_row_count"] == 5, "delta must not replace history"
        assert [r["timestamp"] for r in read_snapshot(store)] == [
            day(i).isoformat() for i in range(5)
        ]
        assert report["prior_dataset_id"] is not None

    def test_an_incremental_run_declares_the_prior_dataset(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_runner(
            tmp_path=tmp_path, store=store, monkeypatch=monkeypatch,
            node=MockDexNode(bars=[bar_row(0)]), end_time=day(0),
        )
        run_runner(
            tmp_path=tmp_path, store=store, monkeypatch=monkeypatch,
            node=MockDexNode(bars=[bar_row(1)]), end_time=day(1),
        )

        catalog = SqliteDatasetCatalog(store.db)
        try:
            dataset_id = catalog.resolve_latest_by_type("dex_pool_ohlcv_daily")
            upstream = catalog.upstream_dataset_ids(str(dataset_id))
        finally:
            catalog.close()
        assert upstream, "the prior canonical snapshot must be a declared dependency"

    def test_rerunning_the_same_range_is_idempotent(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_runner(tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch)
        first = read_snapshot(store)

        code, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch
        )

        # Everything is already at the watermark, so there is nothing to publish and
        # the prior snapshot must survive untouched.
        assert code == 1
        assert report["snapshot_row_count"] == 0
        assert read_snapshot(store) == first

    @pytest.mark.parametrize(
        "node_kwargs",
        [
            {"bars": []},
            {"ohlcv_status": 500},
            {"ohlcv_transport_error": True},
            {"screening_status": 503},
            {"liquidity": 1.0, "volume_24h": 1.0},
        ],
    )
    def test_an_unpublishable_run_exits_nonzero_and_changes_nothing(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch,
        node_kwargs: dict[str, Any],
    ) -> None:
        run_runner(tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch)
        before = read_snapshot(store)
        watermarks_before = WatermarkStore(store.watermark_path).load()

        code, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockDexNode(**node_kwargs),
            monkeypatch=monkeypatch, end_time=day(9),
        )

        assert code == 1
        assert report["snapshot_row_count"] == 0
        assert report["published_dataset_id"] is None
        assert read_snapshot(store) == before, "prior canonical data must survive"
        assert WatermarkStore(store.watermark_path).load() == watermarks_before

    def test_the_report_separates_pool_collections(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch
        )

        assert {"candidate_pools", "passed_pools", "rejected_pools", "unavailable_pools"} <= set(report)
        assert len(report["candidate_pools"]) == 1
        assert len(report["passed_pools"]) == 1
        assert report["passed_pools"][0]["screening"]["status"] == "PASS"
        assert report["passed_pools"][0]["screening"]["liquidity_usd"] == 250_000.0

    def test_the_report_records_lineage_watermarks_and_supersession(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch
        )

        assert report["raw_dependency_count"] >= 3
        assert report["failed_acquisition_count"] == 0
        assert report["live_eligible"] is False
        assert report["catalog_reconciled"] is True
        assert report["thresholds_fingerprint"]
        assert report["supersedes"]["artifact"].endswith("37_DEX_MULTI_PROVIDER_FANOUT.json")
        assert report["supersedes"]["status"] == "SUPERSEDED_PROTOTYPE"

    def test_two_chains_with_the_same_address_publish_separately(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        code, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch,
            pools=[
                {"chain": "arbitrum", "pool_address": POOL},
                {"chain": "base", "pool_address": POOL},
            ],
        )

        assert code == 0
        assert report["snapshot_row_count"] == 10
        chains = {r["chain"] for r in read_snapshot(store)}
        assert chains == {"arbitrum", "base"}

    def test_the_run_uses_a_real_commit_and_config_hash(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run_runner(tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch)

        catalog = SqliteDatasetCatalog(store.db)
        try:
            dataset_id = catalog.resolve_latest_by_type("dex_pool_ohlcv_daily")
            row = catalog.get_dataset(str(dataset_id))
        finally:
            catalog.close()
        assert row is not None
        assert row["code_commit"] == "0" * 40
        assert len(row["config_sha256"]) == 64
        assert set(row["config_sha256"]) != {"0"}


def read_snapshot(store: Store) -> list[dict[str, Any]]:
    catalog = SqliteDatasetCatalog(store.db)
    try:
        dataset_id = catalog.resolve_latest_by_type("dex_pool_ohlcv_daily")
    finally:
        catalog.close()
    if dataset_id is None:
        return []
    parquet = dataset_absolute_dir(store.store_root, dataset_id) / (
        "dex/dex_pool_ohlcv_daily/bars.parquet"
    )
    return pq.read_table(parquet).to_pylist()


# ---------------------------------------------------------------------------
# REVIEW-0236 corrections
# ---------------------------------------------------------------------------

class TestUnresolvedCoverageBlocksPublication:
    """Finding 2: a gap-bearing response must never become canonical data."""

    def _run(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch,
        bars: list[list[Any]],
    ) -> tuple[int, dict[str, Any]]:
        return run_runner(
            tmp_path=tmp_path, store=store, monkeypatch=monkeypatch,
            node=MockDexNode(bars=bars), end_time=day(4),
        )

    def test_an_internal_gap_publishes_nothing(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        code, report = self._run(
            tmp_path, store, monkeypatch, [bar_row(0), bar_row(1), bar_row(3), bar_row(4)]
        )

        assert code == 1
        assert report["published_dataset_id"] is None
        assert report["unresolved_coverage_pools"] == [f"{CHAIN}:{POOL}"]
        assert read_snapshot(store) == []

    def test_a_leading_gap_publishes_nothing(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bars start late: contiguous between themselves, but coverage is short."""
        code, report = self._run(tmp_path, store, monkeypatch, [bar_row(i) for i in (2, 3, 4)])

        assert code == 1
        assert report["published_dataset_id"] is None
        missing = report["passed_pools"][0]["coverage"]["missing_intervals"]
        assert missing == [day(0).isoformat(), day(1).isoformat()]

    def test_a_trailing_gap_publishes_nothing(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        code, report = self._run(tmp_path, store, monkeypatch, [bar_row(i) for i in (0, 1, 2)])

        assert code == 1
        missing = report["passed_pools"][0]["coverage"]["missing_intervals"]
        assert missing == [day(3).isoformat(), day(4).isoformat()]

    def test_unresolved_coverage_advances_no_watermark(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        code, report = self._run(
            tmp_path, store, monkeypatch, [bar_row(0), bar_row(1), bar_row(3), bar_row(4)]
        )

        assert code == 1
        assert report["watermarks_after"] == report["watermarks_before"] == {}
        assert WatermarkStore(store.watermark_path).load() == {}

    def test_exact_coverage_still_publishes(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        code, report = self._run(tmp_path, store, monkeypatch, [bar_row(i) for i in range(5)])

        assert code == 0
        assert report["unresolved_coverage_pools"] == []
        assert report["snapshot_row_count"] == 5

    def test_a_gap_bearing_pool_cannot_ride_along_with_a_clean_one(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """One incomplete pool blocks the whole snapshot, not just its own rows.

        The clean pool has publishable bars, so without the gate its rows would be
        published as a canonical snapshot while its sibling silently lost days.
        """
        code, report = run_runner(
            tmp_path=tmp_path, store=store, monkeypatch=monkeypatch,
            node=MockDexNode(bars_by_pool={
                POOL: [bar_row(i) for i in range(5)],
                POOL_B: [bar_row(0), bar_row(1), bar_row(3), bar_row(4)],
            }),
            pools=[
                {"chain": "arbitrum", "pool_address": POOL},
                {"chain": "base", "pool_address": POOL_B},
            ],
            end_time=day(4),
        )

        assert code == 1, "a clean sibling must not carry a gap-bearing pool into PASS"
        assert report["unresolved_coverage_pools"] == [f"base:{POOL_B}"]
        assert read_snapshot(store) == []
        assert WatermarkStore(store.watermark_path).load() == {}


class TestPriorSnapshotFailsClosed:
    """Finding 3: a missing or corrupt prior output must not become a delta."""

    def _publish_once(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        code, _ = run_runner(
            tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch
        )
        assert code == 0

    def _prior_parquet(self, store: Store) -> Path:
        catalog = SqliteDatasetCatalog(store.db)
        try:
            dataset_id = catalog.resolve_latest_by_type("dex_pool_ohlcv_daily")
        finally:
            catalog.close()
        return dataset_absolute_dir(store.store_root, str(dataset_id)) / (
            "dex/dex_pool_ohlcv_daily/bars.parquet"
        )

    def test_a_missing_prior_output_refuses_to_publish(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._publish_once(tmp_path, store, monkeypatch)
        self._prior_parquet(store).unlink()

        with pytest.raises(RuntimeError, match="refusing to publish a delta"):
            run_runner(
                tmp_path=tmp_path, store=store, monkeypatch=monkeypatch,
                node=MockDexNode(bars=[bar_row(5)]), end_time=day(5),
            )

    def test_a_hash_mismatched_prior_output_refuses_to_publish(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._publish_once(tmp_path, store, monkeypatch)
        parquet = self._prior_parquet(store)
        parquet.write_bytes(parquet.read_bytes() + b"tamper")

        with pytest.raises(RuntimeError, match="does not match the catalog value"):
            run_runner(
                tmp_path=tmp_path, store=store, monkeypatch=monkeypatch,
                node=MockDexNode(bars=[bar_row(5)]), end_time=day(5),
            )

    def test_a_valid_prior_output_reconciles_and_merges(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._publish_once(tmp_path, store, monkeypatch)

        code, report = run_runner(
            tmp_path=tmp_path, store=store, monkeypatch=monkeypatch,
            node=MockDexNode(bars=[bar_row(5)]), end_time=day(5),
        )

        assert code == 0
        prior = report["prior_dataset_reconciliation"]
        assert prior["state"] == "reconciled"
        assert prior["row_count"] == 5
        assert len(prior["file_sha256"]) == 64
        assert report["snapshot_row_count"] == 6


class TestCatalogReconciliationIsProven:
    """Finding 6: compare the published id to the resolved id, do not assert."""

    def test_the_published_and_resolved_ids_are_compared(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        code, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch
        )

        assert code == 0
        reconciliation = report["catalog_reconciliation"]
        assert reconciliation["state"] == "reconciled"
        assert reconciliation["published_dataset_id"] == reconciliation["resolved_dataset_id"]
        assert reconciliation["published_dataset_id"] == report["published_dataset_id"]
        assert reconciliation["catalog_registered"] is True
        assert len(reconciliation["manifest_sha256"]) == 64
        assert len(reconciliation["output_sha256"]) == 64
        assert reconciliation["row_count"] == report["snapshot_row_count"]
        assert report["catalog_reconciled"] is True

    def test_a_reconciliation_mismatch_refuses_to_complete(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If the catalog does not resolve what was published, the run must fail."""
        # The first call is the prior-snapshot lookup (no prior dataset exists);
        # only the post-publish reconciliation lookup returns the wrong id.
        calls = {"n": 0}

        def resolve(self: Any, dataset_type: str) -> str | None:
            calls["n"] += 1
            return None if calls["n"] == 1 else "ds_" + "0" * 64

        monkeypatch.setattr(SqliteDatasetCatalog, "resolve_latest_by_type", resolve)

        with pytest.raises(RuntimeError, match="catalog reconciliation failed"):
            run_runner(
                tmp_path=tmp_path, store=store, node=MockDexNode(), monkeypatch=monkeypatch
            )

    def test_an_unpublished_run_is_not_reported_as_reconciled(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockDexNode(bars=[]), monkeypatch=monkeypatch
        )

        assert report["catalog_reconciled"] is False
        assert report["published_dataset_id"] is None


class TestLegacyPublisherIsDisabled:
    """Finding 1: the superseded path must be impossible to publish through."""

    def test_the_legacy_runner_entry_point_refuses_to_run(self) -> None:
        from scripts.research import dex_multi_provider_fanout as legacy

        assert legacy.main() == 2

    def test_the_legacy_runner_exits_nonzero_as_a_process(self) -> None:
        import subprocess

        result = subprocess.run(
            [sys.executable, "scripts/research/dex_multi_provider_fanout.py", "--no-dry-run"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parents[2]),
        )

        assert result.returncode == 2
        assert "SUPERSEDED" in result.stderr

    def test_the_legacy_screening_default_fails_closed(self) -> None:
        from cryptofactors.ingest.dex_fanout import DexOHLCVProvider

        result = DexOHLCVProvider.screen_pool(
            object.__new__(type("P", (DexOHLCVProvider,), {
                "provider_id": "p", "role": "primary", "fetch_pool_ohlcv": lambda *a, **k: None,
            })),
            chain=CHAIN, pool_address=POOL, min_liquidity_usd=0.0, min_volume_24h_usd=0.0,
        )

        assert result["passed"] is False


class TestRetryAndRateLimits:
    """Retries and rate-limit incidents are required report evidence."""

    def _acquirer(self, store: Store, node: MockDexNode, **kwargs: Any) -> RawHttpAcquirer:
        slept: list[float] = []
        kwargs.setdefault("sleep", slept.append)
        acquirer = RawHttpAcquirer(
            raw_writer=store.writer, client=node.client(), log=AcquisitionLog(), **kwargs
        )
        acquirer.slept = slept  # type: ignore[attr-defined]
        return acquirer

    def test_a_rate_limited_response_is_retried(self, store: Store) -> None:
        node = MockDexNode(ohlcv_status=429)
        acquirer = self._acquirer(store, node, max_attempts=3, backoff_seconds=1.0)

        outcome = acquirer.get_json(
            provider=GECKOTERMINAL_PROVIDER, url="https://api.geckoterminal.com/x",
            source_id="geckoterminal_ohlcv", original_name="x.json",
        )

        assert not outcome.ok
        assert outcome.attempt == 3
        assert len(acquirer.log.outcomes) == 3
        assert len(acquirer.log.rate_limit_incidents) == 3

    def test_backoff_grows_between_attempts(self, store: Store) -> None:
        node = MockDexNode(ohlcv_status=429)
        acquirer = self._acquirer(store, node, max_attempts=4, backoff_seconds=2.0)

        acquirer.get_json(
            provider=GECKOTERMINAL_PROVIDER, url="https://api.geckoterminal.com/x",
            source_id="geckoterminal_ohlcv", original_name="x.json",
        )

        assert acquirer.slept == [2.0, 4.0, 8.0]

    def test_every_attempt_preserves_its_own_response_bytes(self, store: Store) -> None:
        """A 429 body is evidence, not something discarded on the way to a retry."""
        node = MockDexNode(ohlcv_status=429)
        acquirer = self._acquirer(store, node, max_attempts=2, backoff_seconds=0.0)

        acquirer.get_json(
            provider=GECKOTERMINAL_PROVIDER, url="https://api.geckoterminal.com/x",
            source_id="geckoterminal_ohlcv", original_name="x.json",
        )

        assert all(o.raw_object_id is not None for o in acquirer.log.outcomes)

    def test_a_non_retryable_status_is_not_retried(self, store: Store) -> None:
        node = MockDexNode(ohlcv_status=404)
        acquirer = self._acquirer(store, node, max_attempts=5, backoff_seconds=1.0)

        outcome = acquirer.get_json(
            provider=GECKOTERMINAL_PROVIDER, url="https://api.geckoterminal.com/x",
            source_id="geckoterminal_ohlcv", original_name="x.json",
        )

        assert outcome.attempt == 1
        assert acquirer.slept == []

    def test_a_transport_failure_is_retried(self, store: Store) -> None:
        node = MockDexNode(ohlcv_transport_error=True)
        acquirer = self._acquirer(store, node, max_attempts=3, backoff_seconds=0.0)

        outcome = acquirer.get_json(
            provider=GECKOTERMINAL_PROVIDER, url="https://api.geckoterminal.com/x",
            source_id="geckoterminal_ohlcv", original_name="x.json",
        )

        assert outcome.failure_kind == "transport"
        assert outcome.attempt == 3

    def test_a_single_attempt_is_the_default_shape(self, store: Store) -> None:
        node = MockDexNode()
        acquirer = self._acquirer(store, node)

        outcome = acquirer.get_json(
            provider=DEXSCREENER_PROVIDER, url="https://api.dexscreener.com/x",
            source_id="dexscreener_pairs", original_name="x.json",
        )

        assert outcome.ok
        assert outcome.attempt == 1
        assert acquirer.log.retries == []

    def test_the_report_records_retries_and_rate_limit_incidents(
        self, tmp_path: Path, store: Store, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, report = run_runner(
            tmp_path=tmp_path, store=store, node=MockDexNode(ohlcv_status=429),
            monkeypatch=monkeypatch, max_attempts=3,
        )

        assert report["retry_count"] == 2
        assert len(report["rate_limit_incidents"]) == 3
        assert all(i["rate_limited"] for i in report["rate_limit_incidents"])

