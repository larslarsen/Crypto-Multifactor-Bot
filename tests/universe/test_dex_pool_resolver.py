"""Tests for DATA-010 DEX pool resolver."""

from typing import Any

import httpx

from cryptofactors.universe.dex_pool_resolver import (
    DEFAULT_CHAIN_ALLOWLIST,
    SYMBOL_ALIASES,
    DexPoolResolver,
    TOKEN_ADDRESSES,
    U50_TRADING_ASSETS,
)


def _mock_token_pairs_response() -> dict[str, Any]:
    """Minimal DexScreener /tokens/{address} response for two pools."""
    return {
        "schemaVersion": "1.0.0",
        "pairs": [
            {
                "chainId": "arbitrum",
                "dexId": "uniswap",
                "pairAddress": "0x1111111111111111111111111111111111111111",
                "baseToken": {"symbol": "WBTC", "address": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f"},
                "quoteToken": {"symbol": "USDC", "address": "0xaf88d065e77c8cc2239327c5edb3a432268e5831"},
                "liquidity": {"usd": 1_000_000.0},
                "volume": {"h24": 250_000.0},
            },
            {
                "chainId": "arbitrum",
                "dexId": "uniswap",
                "pairAddress": "0x2222222222222222222222222222222222222222",
                "baseToken": {"symbol": "WBTC", "address": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f"},
                "quoteToken": {"symbol": "USDT", "address": "0xfd086bc7cd5c48d4637b3c83f24d6e2b44d4dce2"},
                "liquidity": {"usd": 500_000.0},
                "volume": {"h24": 100_000.0},
            },
        ],
    }


def _make_mock_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if "api.dexscreener.com" in str(request.url):
            return httpx.Response(200, json=_mock_token_pairs_response())
        return httpx.Response(404, text="unmocked")

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_resolve_pool_returns_top_n_usdc_usdt_pairs() -> None:
    resolver = DexPoolResolver(client=_make_mock_client(), chain_allowlist={"arbitrum"})
    pools = resolver.resolve_pool(
        "BTC",
        min_liquidity_usd=0.0,
        min_volume_24h_usd=0.0,
        top_n=2,
    )
    assert len(pools) == 2
    assert pools[0]["address"] == "0x1111111111111111111111111111111111111111"
    assert pools[0]["symbol"] == "BTC"
    assert pools[0]["chain"] == "arbitrum"
    assert pools[0]["gecko_network"] == "arbitrum"
    assert pools[0]["base_token"] == "WBTC"
    assert pools[0]["quote_token"] == "USDC"
    assert pools[0]["liquidity_usd"] == 1_000_000.0
    assert pools[0]["volume_24h_usd"] == 250_000.0
    assert pools[1]["address"] == "0x2222222222222222222222222222222222222222"


def test_resolve_pool_ignores_non_quote_pairs() -> None:
    response = _mock_token_pairs_response()
    response["pairs"].append({
        "chainId": "arbitrum",
        "dexId": "uniswap",
        "pairAddress": "0x3333333333333333333333333333333333333333",
        "baseToken": {"symbol": "WBTC", "address": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f"},
        "quoteToken": {"symbol": "WETH", "address": "0x82af49447d8a07e3bd95bd0d56f35241523fbab1"},
        "liquidity": {"usd": 2_000_000.0},
        "volume": {"h24": 500_000.0},
    })

    def handler(request: httpx.Request) -> httpx.Response:
        if "api.dexscreener.com" in str(request.url):
            return httpx.Response(200, json=response)
        return httpx.Response(404, text="unmocked")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    resolver = DexPoolResolver(client=client, chain_allowlist={"arbitrum"})
    pools = resolver.resolve_pool("BTC", min_liquidity_usd=0.0, min_volume_24h_usd=0.0, top_n=3)
    assert len(pools) == 2
    assert all(p["quote_token"] in {"USDC", "USDT"} for p in pools)


def test_resolve_pool_filters_by_liquidity_and_volume() -> None:
    resolver = DexPoolResolver(client=_make_mock_client(), chain_allowlist={"arbitrum"})
    pools = resolver.resolve_pool(
        "BTC",
        min_liquidity_usd=600_000.0,
        min_volume_24h_usd=150_000.0,
        top_n=3,
    )
    assert len(pools) == 1
    assert pools[0]["address"] == "0x1111111111111111111111111111111111111111"


def test_resolve_pool_unknown_symbol_returns_empty() -> None:
    resolver = DexPoolResolver(client=_make_mock_client())
    assert resolver.resolve_pool("UNKNOWN") == []


def test_resolve_universe_returns_pools_for_multiple_assets() -> None:
    resolver = DexPoolResolver(client=_make_mock_client())
    pools = resolver.resolve_universe(["BTC", "ETH"], top_n=2)
    assert len(pools) >= 2
    assert all(p["symbol"] in {"BTC", "ETH"} for p in pools)


def test_u50_assets_list_has_expected_size() -> None:
    # U50+ trading assets listed in DATA-010.
    assert len(U50_TRADING_ASSETS) >= 20


def test_all_u50_assets_have_token_addresses() -> None:
    missing = [sym for sym in U50_TRADING_ASSETS if sym not in TOKEN_ADDRESSES]
    # Some native/non-EVM assets are intentionally omitted from the static mapping.
    assert set(missing) <= {"SUI", "SEI", "FIL", "BCH"}


def test_chain_allowlist_includes_base() -> None:
    assert "base" in DEFAULT_CHAIN_ALLOWLIST


def test_symbol_aliases_cover_wrapped_assets() -> None:
    assert "cbDOGE" in SYMBOL_ALIASES["DOGE"]
    assert "cbXRP" in SYMBOL_ALIASES["XRP"]
    assert "cbADA" in SYMBOL_ALIASES["ADA"]
    assert "cbLTC" in SYMBOL_ALIASES["LTC"]
    assert "WBTC" in SYMBOL_ALIASES["BTC"]
    assert "WETH" in SYMBOL_ALIASES["ETH"]


def test_gecko_network_mapping_for_ethereum() -> None:
    from cryptofactors.universe.dex_pool_resolver import GECKO_NETWORKS
    assert GECKO_NETWORKS["ethereum"] == "eth"
    assert GECKO_NETWORKS["arbitrum"] == "arbitrum"
    assert GECKO_NETWORKS["base"] == "base"
