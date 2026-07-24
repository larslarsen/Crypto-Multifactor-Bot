"""DATA-010 — DEX pool resolver for U50+ trading assets.

Resolves the highest-liquidity USDC/USDT pool address for each U50+ trading
asset using the DexScreener free API. The resolver uses known token contract
addresses on Ethereum/Arbitrum to query DexScreener's token-pair endpoint, then
filters for USDC/USDT quote pairs and selects the highest-liquidity pool on an
EVM-compatible chain (ethereum, arbitrum, polygon, optimism) so that
GeckoTerminal's free OHLCV API can consume the address.

No Birdeye OHLCV.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from cryptofactors.ingest.dex_fanout import TokenBucketRateLimiter

# U50+ trading assets named in DATA-010.
# GeckoTerminal network identifiers differ from the chain labels used by
# DexScreener. Map the canonical chain id to the GeckoTerminal network slug.
GECKO_NETWORKS: dict[str, str] = {
    "ethereum": "eth",
    "arbitrum": "arbitrum",
    "polygon": "matic",
    "optimism": "optimism",
    "base": "base",
    "solana": "solana",
}

U50_TRADING_ASSETS: list[str] = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "AVAX",
    "DOT",
    "LINK",
    "LTC",
    "BCH",
    "DOGE",
    "UNI",
    "AAVE",
    "CRV",
    "APE",
    "NEAR",
    "FIL",
    "ARB",
    "OP",
    "SUI",
    "SEI",
    "WLD",
    "PEPE",
]

# Known token contract addresses for EVM-compatible chains. Wrapped/bridged
# tokens are used where the native asset is not EVM-native (e.g. WBTC for BTC).
# Addresses are sourced from CoinGecko / public token lists.
TOKEN_ADDRESSES: dict[str, dict[str, str]] = {
    "BTC": {
        "ethereum": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # WBTC
        "arbitrum": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",  # WBTC
        "base": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",  # cbBTC
    },
    "ETH": {
        "ethereum": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
        "arbitrum": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",  # WETH
        "optimism": "0x4200000000000000000000000000000000000006",  # WETH
        "polygon": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH
    },
    "LINK": {
        "ethereum": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
        "arbitrum": "0xf97f4df75117a78c1A5a0DBb814Af92458539FB4",
        "polygon": "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39",
    },
    "UNI": {
        "ethereum": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "arbitrum": "0xFa7F8980b0f1Ae64b206ecd4D4C9b0d9D1C0bB3f",
        "polygon": "0xb33EaAd8d922B1083446DC23f610c2567fB518Cb",
    },
    "AAVE": {
        "ethereum": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        "arbitrum": "0xba5DdD1f9d7F570dC94Dc0aaDb683C6bf9bE074e",
        "polygon": "0xD6DF932A45C0f255f85145f286eA0a2927aF40Da",
    },
    "CRV": {
        "ethereum": "0xD533a949740bb3306d119CC777fa00bD10247eAe",
        "arbitrum": "0x11cDb42B0EB46D95f990BeDD9975A8bd637eaD52",
        "polygon": "0x172370d5Cd63263e6e2Dc8ee21E9A47e6B9Db4E7",
        "base": "0x8ee73c484a26e0a5df2ee2a4960b789967dd0415",  # CoinGecko Base
    },
    "APE": {
        "ethereum": "0x4d224452801ACEd8B2F0aebE1553bb5b5bC243b8",
        "arbitrum": "0x7f9fbf9bdd3f4105c478b996b648fe6e828a1e98",
        "polygon": "0xb7b31a6bc18e48888545ce79e83e06003be70930",
    },
    "ARB": {
        "ethereum": "0xB50721BCf8d664c30432CfE8c544b0b62D093c9e",
        "arbitrum": "0x912CE59144191C1204E64559FE8253a0e49E6548",
    },
    "OP": {
        "ethereum": "0x4200000000000000000000000000000000000042",
        "optimism": "0x4200000000000000000000000000000000000042",
    },
    "WLD": {
        "ethereum": "0x163f8c2467924be0ae7b5347228cabf260318753",
        "optimism": "0xdc6ff44d5d932cbd77b52e5612ba0529dc6226f1",
    },
    "PEPE": {
        "ethereum": "0x6982508145454Ce325dDbE47a25d4ec3d2311933",
        "arbitrum": "0x25d887ce7a35172c62febfd67a1856f20faebb00",
    },
    "NEAR": {
        "ethereum": "0x85F17Cf997934a597031b2e18a9AB6EBd4b9f6a4",  # wrapped NEAR
    },
    "SOL": {
        "ethereum": "0xD31a59c85aE9D8edEFeC411D448f90841571b89c",  # Wormhole SOL
    },
    "DOGE": {
        "base": "0xcbd06e5a2b0c65597161de254aa074e489deb510",  # cbDOGE
    },
    "XRP": {
        "base": "0xcb585250f852C6c6bf90434AB21A00f02833a4af",  # cbXRP
        "ethereum": "0x39fBBABf11738317a448031930706cd3e612e1B9",  # wXRP
    },
    "ADA": {
        "base": "0xcbADA732173e39521CDBE8bf59a6Dc85A9fc7b8c",  # cbADA
    },
    "LTC": {
        "base": "0xcb17C9Db87B595717C857a08468793f5bAb6445F",  # cbLTC
    },
    "AVAX": {
        "ethereum": "0x85f138bfEE4ef8e540890CFb48F620571d67Eda3",  # Wormhole WAVAX
    },
    "DOT": {
        "ethereum": "0x196c20da81fbc324ecdf55501e95ce9f0bd84d14",  # Snowbridge DOT
    },
    # SUI, SEI, FIL, and BCH are native/non-EVM assets for which we have not
    # identified liquid, GeckoTerminal-tracked USDC/USDT pools on the supported
    # EVM chains. They are intentionally omitted from the static mapping.
}

DEFAULT_CHAIN_ALLOWLIST: set[str] = {"ethereum", "arbitrum", "polygon", "optimism", "base", "solana"}
DEFAULT_QUOTE_TOKENS: set[str] = {"USDC", "USDT", "USDCE", "USDT0", "USD₮0"}

# DexScreener labels wrapped tokens as WETH/WBTC instead of ETH/BTC. Coinbase
# wrapped assets on Base use the "cb" prefix (cbDOGE, cbXRP, cbADA, cbLTC).
SYMBOL_ALIASES: dict[str, set[str]] = {
    "BTC": {"WBTC", "cbBTC"},
    "ETH": {"WETH"},
    "DOGE": {"cbDOGE", "renDOGE"},
    "XRP": {"cbXRP", "wXRP", "Wrapped XRP"},
    "ADA": {"cbADA", "Wrapped ADA"},
    "LTC": {"cbLTC", "Wrapped LTC"},
    "AVAX": {"WAVAX", "Wrapped AVAX"},
    "SOL": {"SOL", "Wrapped SOL"},
    "DOT": {"DOT", "Polkadot"},
    "SUI": {"SUI", "Wrapped SUI"},
    "SEI": {"SEI", "Wrapped SEI"},
    "FIL": {"FIL", "Wrapped FIL"},
    "BCH": {"BCH", "Bitcoin Cash"},
}
# DexScreener public API is generous; keep a polite 30 req/min.
DEFAULT_RATE_PER_MIN: float = 30.0


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


class DexPoolResolver:
    """Resolve a symbol → highest-liquidity USDC/USDT pool address on an EVM chain."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
        chain_allowlist: set[str] | None = None,
        quote_tokens: set[str] | None = None,
    ) -> None:
        self._client: httpx.Client | None = client
        self._rate_limiter = rate_limiter or TokenBucketRateLimiter(
            tokens_per_second=DEFAULT_RATE_PER_MIN / 60.0,
        )
        self._chain_allowlist = set(chain_allowlist) if chain_allowlist else DEFAULT_CHAIN_ALLOWLIST
        self._quote_tokens = {q.upper() for q in (quote_tokens or DEFAULT_QUOTE_TOKENS)}

    def resolve_pool(
        self,
        symbol: str,
        *,
        min_liquidity_usd: float = 0.0,
        min_volume_24h_usd: float = 0.0,
        top_n: int = 3,
    ) -> list[dict[str, Any]]:
        """Return the top N pool dicts for ``symbol`` that pass filters."""
        sym = _normalize_symbol(symbol)
        token_addresses = TOKEN_ADDRESSES.get(sym)
        if not token_addresses:
            return []

        pairs: list[dict[str, Any]] = []
        for chain, address in token_addresses.items():
            if chain not in self._chain_allowlist:
                continue
            self._rate_limiter.acquire(provider="dexscreener_resolver", chain=chain, pool_address=sym)
            chain_pairs = self._fetch_token_pairs(address)
            pairs.extend(chain_pairs)

        candidates = self._filter_pairs(pairs, symbol=sym)
        if not candidates:
            return []
        ranked = self._rank_pairs(candidates)
        out: list[dict[str, Any]] = []
        for best in ranked[:top_n]:
            liquidity = float(best.get("liquidity", {}).get("usd") or 0.0)
            volume_24h = float(best.get("volume", {}).get("h24") or 0.0)
            if liquidity < min_liquidity_usd or volume_24h < min_volume_24h_usd:
                continue
            chain_id = str(best.get("chainId") or "").lower()
            out.append({
                "symbol": sym,
                "chain": chain_id,
                "gecko_network": GECKO_NETWORKS.get(chain_id, chain_id),
                "address": str(best.get("pairAddress") or "").lower(),
                "fee_tier": self._infer_fee_tier(best),
                "liquidity_usd": liquidity,
                "volume_24h_usd": volume_24h,
                "dex_id": str(best.get("dexId") or ""),
                "base_token": best.get("baseToken", {}).get("symbol"),
                "quote_token": best.get("quoteToken", {}).get("symbol"),
            })
        return out

    def resolve_universe(
        self,
        symbols: Sequence[str],
        *,
        min_liquidity_usd: float = 0.0,
        min_volume_24h_usd: float = 0.0,
        top_n: int = 3,
    ) -> list[dict[str, Any]]:
        """Resolve pools for a list of symbols and return those that pass filters."""
        pools: list[dict[str, Any]] = []
        for sym in symbols:
            resolved = self.resolve_pool(
                sym,
                min_liquidity_usd=min_liquidity_usd,
                min_volume_24h_usd=min_volume_24h_usd,
                top_n=top_n,
            )
            pools.extend(resolved)
        return pools

    def _fetch_token_pairs(self, token_address: str) -> list[dict[str, Any]]:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        try:
            if self._client:
                r = self._client.get(url)
            else:
                with httpx.Client(timeout=30.0) as c:
                    r = c.get(url)
        except Exception:  # noqa: BLE001
            return []
        if r.status_code != 200:
            return []
        data = r.json()
        if not isinstance(data, dict):
            return []
        return list(data.get("pairs") or [])

    def _filter_pairs(self, pairs: Sequence[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        aliases = SYMBOL_ALIASES.get(symbol, set()) | {symbol}
        for p in pairs:
            if not isinstance(p, dict):
                continue
            chain = str(p.get("chainId") or "").lower()
            if chain not in self._chain_allowlist:
                continue
            base = str(p.get("baseToken", {}).get("symbol") or "").upper()
            quote = str(p.get("quoteToken", {}).get("symbol") or "").upper()
            if base not in aliases and quote not in aliases:
                continue
            if quote not in self._quote_tokens and base not in self._quote_tokens:
                continue
            # Only keep pairs where the target asset is the base token so that
            # GeckoTerminal's token=base OHLCV returns the asset price directly.
            if base not in aliases:
                continue
            out.append(p)
        return out

    def _rank_pairs(self, pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Prefer Arbitrum, then Ethereum, then other EVM chains, then Solana.

        Arbitrum has the best GeckoTerminal public-API coverage for DEX-002.
        """
        chain_order = {
            "arbitrum": 0,
            "ethereum": 1,
            "polygon": 2,
            "optimism": 3,
            "base": 4,
            "solana": 5,
        }
        return sorted(
            pairs,
            key=lambda p: (
                chain_order.get(str(p.get("chainId") or "").lower(), 99),
                -(p.get("liquidity", {}).get("usd") or 0.0),
            ),
        )

    @staticmethod
    def _infer_fee_tier(pair: dict[str, Any]) -> str | None:
        labels = pair.get("labels") or []
        if isinstance(labels, list):
            for label in labels:
                if isinstance(label, str) and "%" in label:
                    return label
        return None


def score_pool(pool: dict[str, Any]) -> float:
    """Composite priority score: sqrt(liquidity * volume_24h)."""
    liq = float(pool.get("liquidity_usd") or 0.0)
    vol = float(pool.get("volume_24h_usd") or 0.0)
    return (liq * vol) ** 0.5
