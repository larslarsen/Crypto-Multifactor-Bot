"""Tests for DATA-007 free source rate-limit probes.

All network calls are mocked; no API keys are required in CI.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from cryptofactors.acquisition.free_source_probes import (
    ALL_PROBES,
    BinancePublicProbe,
    BirdeyeListingsProbe,
    BitmexFundingProbe,
    DefiLlamaProbe,
    DexScreenerProbe,
    GeckoTerminalProbe,
    SourceProbe,
    build_matrix_report,
    recommended_fanout,
)


def _ok_response(payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json=payload)


def _build_mock_for(probe: SourceProbe) -> httpx.Client:
    """Return a mock client that returns 200 for the expected probe URL."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "geckoterminal" in url:
            return _ok_response({"data": {"attributes": {"name": "USDC/USDT"}}})
        if "birdeye" in url:
            return _ok_response({"success": True, "data": {"items": []}})
        if "dexscreener" in url:
            return _ok_response({"pairs": []})
        if "llama" in url:
            return _ok_response({"status": "ok", "data": []})
        if "binance" in url:
            return _ok_response({"symbols": []})
        if "bitmex" in url:
            return _ok_response([])
        return httpx.Response(404, text="not found")

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize("probe_cls", ALL_PROBES)
def test_probe_returns_result_dry_run(probe_cls: type[SourceProbe]) -> None:
    """Every probe returns a complete row in dry-run mode."""
    probe = probe_cls()
    result = probe.probe(live=False)
    assert result.source_id
    assert result.role in (
        "cex_bars",
        "funding",
        "dex_ohlcv",
        "dex_listings",
        "pool_stats",
    )
    assert result.probe_status in ("ok", "partial", "fail")
    assert result.probe_method == "mocked"


@pytest.mark.parametrize("probe_cls", ALL_PROBES)
def test_probe_live_with_mock_client(probe_cls: type[SourceProbe]) -> None:
    """Every probe can run live with a mock client."""
    probe = probe_cls()
    mock = _build_mock_for(probe)
    result = probe.probe(live=True, mock=mock)
    assert result.probe_method == "live"
    assert result.probe_status == "ok"


def test_birdeye_row_forbids_ohlcv() -> None:
    """Birdeye probe must set birdeye_ohlcv_forbidden=True."""
    result = BirdeyeListingsProbe().probe(live=False)
    assert result.birdeye_ohlcv_forbidden is True
    assert result.role == "dex_listings"
    assert result.env_key_name == "BIRDEYE_API_KEY"
    endpoints = {e.path for e in result.endpoints}
    assert all("ohlcv" not in path.lower() for path in endpoints)
    assert all("bar" not in path.lower() for path in endpoints)


def test_geckoterminal_is_dex_ohlcv() -> None:
    result = GeckoTerminalProbe().probe(live=False)
    assert result.role == "dex_ohlcv"
    assert result.auth_model == "none"
    assert result.history_depth


def test_dexscreener_is_pool_stats() -> None:
    result = DexScreenerProbe().probe(live=False)
    assert result.role == "pool_stats"


def test_defillama_is_pool_stats() -> None:
    result = DefiLlamaProbe().probe(live=False)
    assert result.role == "pool_stats"


def test_binance_is_cex_bars() -> None:
    result = BinancePublicProbe().probe(live=False)
    assert result.role == "cex_bars"


def test_bitmex_is_funding() -> None:
    result = BitmexFundingProbe().probe(live=False)
    assert result.role == "funding"


def test_build_matrix_report() -> None:
    report = build_matrix_report(live=False)
    assert report["experiment_id"] == "DATA-007-FREE-SOURCE-RATE-LIMIT-MATRIX"
    assert not report["live_eligible"]
    assert len(report["sources"]) == len(ALL_PROBES)
    assert report["recommended_fanout"]
    assert "estimated_daily_capacity" in report
    birdeye = next(r for r in report["sources"] if r["source_id"] == "birdeye_listings")
    assert birdeye["birdeye_ohlcv_forbidden"] is True


def test_recommended_fanout_order() -> None:
    fanout = recommended_fanout()
    assert fanout[0] == "geckoterminal"
    assert "dexscreener" in fanout
    assert "defillama" in fanout


def test_birdeye_live_without_key_is_fail() -> None:
    """If BIRDEYE_API_KEY is absent, live Birdeye probe must fail gracefully."""
    import os

    orig = os.environ.pop("BIRDEYE_API_KEY", None)
    try:
        result = BirdeyeListingsProbe().probe(live=True)
        assert result.probe_status == "fail"
        assert "BIRDEYE_API_KEY" in result.notes
    finally:
        if orig is not None:
            os.environ["BIRDEYE_API_KEY"] = orig
