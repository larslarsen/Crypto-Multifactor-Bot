"""Tests for FUND-005 BitMEX funding rate ingestion and provider."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pyarrow.parquet as pq
import pytest

from cryptofactors.ingest.bitmex_funding import (
    BITMEX_FUNDING_SCHEMA,
    BitMEXFundingClient,
    BitMEXFundingError,
    BitMEXFundingProvider,
    build_funding_table,
    normalize_funding_record,
)


def sample_raw_bitmex_funding() -> list[dict[str, Any]]:
    return [
        {
            "timestamp": "2026-07-22T04:00:00.000Z",
            "symbol": "XBTUSD",
            "fundingInterval": "2000-01-01T08:00:00.000Z",
            "fundingRate": 0.0001,
            "fundingRateDaily": 0.0003,
        },
        {
            "timestamp": "2026-07-22T12:00:00.000Z",
            "symbol": "XBTUSD",
            "fundingInterval": "2000-01-01T08:00:00.000Z",
            "fundingRate": 0.0002,
            "fundingRateDaily": 0.0006,
        },
        {
            "timestamp": "2026-07-22T20:00:00.000Z",
            "symbol": "XBTUSD",
            "fundingInterval": "2000-01-01T08:00:00.000Z",
            "fundingRate": -0.0001,
            "fundingRateDaily": -0.0003,
        },
    ]


def test_normalize_funding_record() -> None:
    raw = sample_raw_bitmex_funding()[0]
    norm = normalize_funding_record(raw)

    assert norm["symbol"] == "XBTUSD"
    assert norm["funding_rate"] == 0.0001
    assert norm["funding_rate_daily"] == 0.0003
    assert norm["source"] == "bitmex_funding"
    assert norm["timestamp"] == "2026-07-22T04:00:00Z"
    assert norm["timestamp_us"] == int(
        datetime(2026, 7, 22, 4, 0, tzinfo=timezone.utc).timestamp() * 1_000_000
    )


def test_build_funding_table() -> None:
    raw_list = sample_raw_bitmex_funding()
    table = build_funding_table(raw_list)

    assert table.num_rows == 3
    assert table.schema == BITMEX_FUNDING_SCHEMA
    assert table.column("symbol").to_pylist() == ["XBTUSD", "XBTUSD", "XBTUSD"]


def test_client_fetch_funding_pagination() -> None:
    mock_responses = [
        sample_raw_bitmex_funding()[:2],
        sample_raw_bitmex_funding()[2:],
    ]
    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        data = mock_responses[call_count] if call_count < len(mock_responses) else []
        call_count += 1
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    funding_client = BitMEXFundingClient(client=client, requests_per_minute=1000)
    records = funding_client.fetch_funding(
        symbol="XBTUSD",
        start_time=datetime(2026, 7, 22, tzinfo=timezone.utc),
        count=2,
    )

    assert len(records) == 3
    assert call_count == 2
    assert records[0]["timestamp"] == "2026-07-22T04:00:00Z"


def test_provider_get_funding_events_and_cashflow() -> None:
    raw_list = sample_raw_bitmex_funding()
    provider = BitMEXFundingProvider.from_records(raw_list)

    t_start = datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 7, 22, 23, 59, tzinfo=timezone.utc)

    events = provider.get_funding_events("XBTUSD", t_start, t_end)
    assert len(events) == 3

    # Long position of $100,000 XBTUSD
    # Event 1 (+0.0001): long pays $10 -> cashflow -10
    # Event 2 (+0.0002): long pays $20 -> cashflow -20
    # Event 3 (-0.0001): long receives $10 -> cashflow +10
    # Total cashflow = -20 USD
    cf_long = provider.compute_funding_cashflow(
        "XBTUSD",
        position_qty=100_000.0,
        start_time=t_start,
        end_time=t_end,
        is_inverse=True,
        mark_price=50_000.0,
    )
    assert pytest.approx(cf_long, abs=1e-5) == -20.0

    # Short position of $100,000 XBTUSD
    # Short position receives opposite (+20 USD)
    cf_short = provider.compute_funding_cashflow(
        "XBTUSD",
        position_qty=-100_000.0,
        start_time=t_start,
        end_time=t_end,
        is_inverse=True,
        mark_price=50_000.0,
    )
    assert pytest.approx(cf_short, abs=1e-5) == 20.0


def test_provider_parquet_roundtrip() -> None:
    raw_list = sample_raw_bitmex_funding()
    table = build_funding_table(raw_list)

    with tempfile.TemporaryDirectory() as tmpdir:
        pq_path = Path(tmpdir) / "funding.parquet"
        pq.write_table(table, str(pq_path))

        provider = BitMEXFundingProvider.from_parquet(pq_path)
        events = provider.get_funding_events(
            "XBTUSD",
            datetime(2026, 7, 22, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 22, 23, 59, tzinfo=timezone.utc),
        )
        assert len(events) == 3


def test_invalid_records_fail_closed() -> None:
    with pytest.raises(BitMEXFundingError, match="missing valid ISO timestamp"):
        normalize_funding_record({"symbol": "XBTUSD", "fundingRate": 0.0001})

    with pytest.raises(BitMEXFundingError, match="missing symbol"):
        normalize_funding_record({"timestamp": "2026-07-22T04:00:00Z", "fundingRate": 0.0001})
