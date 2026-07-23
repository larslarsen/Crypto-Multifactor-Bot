"""Tests for UNIVERSE-002 Birdeye DEX listings provider."""

import inspect
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from cryptofactors.universe import (
    BirdeyeListingsError,
    BirdeyeListingsProvider,
    build_birdeye_listings_table,
    normalize_listing_event,
)
import cryptofactors.universe.birdeye_listings as birdeye_module


def sample_raw_listing() -> dict[str, Any]:
    return {
        "address": "So11111111111111111111111111111111111111112",
        "symbol": "SOL",
        "name": "Wrapped Solana",
        "decimals": 9,
        "liquidityAddedAt": "2023-01-01T00:00:00.000Z",
        "liquidity": 1000000.0,
        "source": "raydium",
    }


def test_guard_against_ohlcv_or_bar_endpoints() -> None:
    """Acceptance item #5: Assert no OHLCV or bar endpoint string/logic exists in birdeye_listings."""
    source_code = inspect.getsource(birdeye_module).lower()

    prohibited = ["ohlcv", "kline", "history_price", "/history", "/bars", "/candle"]
    for term in prohibited:
        assert term not in source_code, f"Forbidden bar/OHLCV term '{term}' found in birdeye_listings.py"


def test_non_survivorship_free_labeling_on_every_row() -> None:
    raw = sample_raw_listing()
    norm = normalize_listing_event(raw, chain="solana")

    assert "survivorship_free" in norm
    assert norm["survivorship_free"] is False
    assert norm["source"] == "birdeye_new_listing"

    table = build_birdeye_listings_table([raw])
    rows = table.to_pylist()
    assert len(rows) == 1
    assert rows[0]["survivorship_free"] is False
    assert rows[0]["source"] == "birdeye_new_listing"


def test_normalization_validation() -> None:
    with pytest.raises(BirdeyeListingsError, match="missing required 'address'"):
        normalize_listing_event({"symbol": "NO_ADDR"})


def test_point_in_time_membership_queries() -> None:
    records = [
        {
            "address": "token_a",
            "symbol": "TKNA",
            "liquidityAddedAt": "2025-01-01T00:00:00Z",
        },
        {
            "address": "token_b",
            "symbol": "TKNB",
            "liquidityAddedAt": "2025-06-01T00:00:00Z",
        },
    ]
    provider = BirdeyeListingsProvider.from_records(records)

    # Before token_a listing
    t0 = datetime(2024, 12, 31, tzinfo=timezone.utc)
    assert provider.universe_at(t0) == []

    # After token_a, before token_b
    t1 = datetime(2025, 3, 1, tzinfo=timezone.utc)
    assert provider.universe_at(t1) == ["token_a"]

    # After token_b listing
    t2 = datetime(2025, 7, 1, tzinfo=timezone.utc)
    assert provider.universe_at(t2) == ["token_a", "token_b"]

    # Events since t1
    events = provider.universe_events_since(t1)
    assert len(events) == 1
    assert events[0]["address"] == "token_b"


def test_fetch_new_listings_uses_only_new_listing_endpoint() -> None:
    calls: list[str] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {"items": [sample_raw_listing()]},
            },
        )

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    provider = BirdeyeListingsProvider(api_key="test_key", client=client)
    res = provider.fetch_new_listings(chain="solana", limit=10)

    assert len(res) == 1
    assert len(calls) == 1
    assert "/defi/v2/tokens/new_listing" in calls[0]
    assert "ohlcv" not in calls[0].lower()
