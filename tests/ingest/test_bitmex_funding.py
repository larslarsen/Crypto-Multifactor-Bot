"""Tests for FUND-005 BitMEX funding rate ingestion and provider."""

import json
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
    collapse_funding_observations,
    format_funding_request_bound,
    normalize_funding_record,
    require_exact_microsecond_timestamp,
    validate_funding_history,
)

_FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "bitmex_funding_source_shapes.json"
)


def _source_shapes() -> dict[str, Any]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


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


def test_synthetic_source_shapes_fail_closed() -> None:
    shapes = _source_shapes()
    official = normalize_funding_record(shapes["official_raw_success"])
    assert official["funding_rate"] == 0.0001
    assert official["funding_rate_daily"] == 0.0003
    assert official["funding_interval"].startswith("2000-01-01")
    assert official["availability_time"] is None
    assert official["source"] == "bitmex_funding"

    supplied = normalize_funding_record(shapes["supplied_daily_not_three_times_rate"])
    assert supplied["funding_rate"] == 0.0001
    assert supplied["funding_rate_daily"] == 0.0005
    assert supplied["timestamp"] == "2020-01-01T04:00:00.123456Z"
    assert supplied["availability_time"] is None

    with pytest.raises(BitMEXFundingError, match="empty required funding interval"):
        normalize_funding_record(shapes["retained_normalized_invalid"])

    with pytest.raises(BitMEXFundingError, match="source-field drift"):
        normalize_funding_record(shapes["drifted_snake_only"])

    with pytest.raises(BitMEXFundingError, match="source-field drift"):
        normalize_funding_record(shapes["missing_funding_rate"])

    with pytest.raises(BitMEXFundingError, match="empty required funding interval"):
        normalize_funding_record(shapes["empty_funding_interval"])

    with pytest.raises(BitMEXFundingError, match="numeric JSON"):
        normalize_funding_record(shapes["non_finite_rate"])

    with pytest.raises(BitMEXFundingError, match="boolean"):
        normalize_funding_record(shapes["boolean_rate"])

    with pytest.raises(BitMEXFundingError, match="missing fundingRate"):
        normalize_funding_record(shapes["null_rate"])

    with pytest.raises(BitMEXFundingError, match="nonempty string"):
        normalize_funding_record(shapes["wrong_type_symbol"])

    with pytest.raises(BitMEXFundingError, match="contradict"):
        normalize_funding_record(shapes["mixed_aliases"])


def test_missing_rate_is_not_converted_to_zero() -> None:
    with pytest.raises(BitMEXFundingError, match="source-field drift"):
        normalize_funding_record(
            {
                "timestamp": "2020-01-01T04:00:00.000Z",
                "symbol": "XBTUSD",
                "fundingInterval": "2000-01-01T08:00:00.000Z",
                "fundingRateDaily": 0.0003,
            }
        )


def test_all_zero_nontrivial_history_is_rejected() -> None:
    records = [
        {
            "timestamp": "2020-01-01T04:00:00.000Z",
            "symbol": "XBTUSD",
            "fundingInterval": "2000-01-01T08:00:00.000Z",
            "fundingRate": 0.0,
            "fundingRateDaily": 0.0,
        },
        {
            "timestamp": "2020-01-01T12:00:00.000Z",
            "symbol": "XBTUSD",
            "fundingInterval": "2000-01-01T08:00:00.000Z",
            "fundingRate": 0.0,
            "fundingRateDaily": 0.0,
        },
    ]
    with pytest.raises(BitMEXFundingError, match="all-zero nontrivial"):
        build_funding_table(records)


def test_single_zero_rate_event_is_allowed() -> None:
    table = build_funding_table(
        [
            {
                "timestamp": "2020-01-01T04:00:00.000Z",
                "symbol": "XBTUSD",
                "fundingInterval": "2000-01-01T08:00:00.000Z",
                "fundingRate": 0.0,
                "fundingRateDaily": 0.0,
            }
        ]
    )
    validate_funding_history(table)
    assert table.num_rows == 1


def test_fetch_perp_symbols() -> None:
    instruments = [
        {"symbol": "XBTUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "ETHUSD", "typ": "FFWCSX", "state": "Open"},
        {"symbol": "SPYUSD", "typ": "FFCCSX", "state": "Open"},
        {"symbol": "UNLISTED", "typ": "FFWCSX", "state": "Unlisted"},
    ]

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if "/instrument/active" in str(request.url):
            return httpx.Response(200, json=instruments)
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(mock_handler)
    client = BitMEXFundingClient(client=httpx.Client(transport=transport), requests_per_minute=1000)
    symbols = client.fetch_perp_symbols()
    assert symbols == ["ETHUSD", "XBTUSD"]


def test_fetch_perp_symbols_can_include_all_states() -> None:
    instruments = [
        {"symbol": "XBTUSD", "typ": "FFWCSX", "state": "Unlisted"},
    ]

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=instruments)

    transport = httpx.MockTransport(mock_handler)
    client = BitMEXFundingClient(client=httpx.Client(transport=transport), requests_per_minute=1000)
    assert client.fetch_perp_symbols(state=None) == ["XBTUSD"]
    assert client.fetch_perp_symbols(state="Open") == []


def test_backfill_publication_blockers() -> None:
    import importlib.util

    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "research"
        / "backfill_bitmex_funding.py"
    )
    spec = importlib.util.spec_from_file_location("backfill_bitmex_funding", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    blockers = module.publication_blockers

    assert blockers(fetch_errors=[], symbols_empty=[], missing_requested=[]) == []
    assert "fetch_errors" in blockers(
        fetch_errors=[{"symbol": "XBTUSD"}],
        symbols_empty=[],
        missing_requested=[],
    )
    assert "empty_requested_symbols" in blockers(
        fetch_errors=[],
        symbols_empty=["XBTUSD"],
        missing_requested=[],
    )
    assert "incomplete_requested_coverage" in blockers(
        fetch_errors=[],
        symbols_empty=[],
        missing_requested=["ETHUSD"],
    )
    assert "missing_in_window_coverage" in blockers(
        fetch_errors=[],
        symbols_empty=[],
        missing_requested=[],
        missing_in_window=["XBTUSD"],
    )


def _path_signature(path: Path) -> tuple[bool, int | None, bytes | None]:
    if not path.exists():
        return (False, None, None)
    if path.is_file():
        return (True, path.stat().st_ino, path.read_bytes())
    return (True, path.stat().st_ino, None)


def test_full_backfill_script_dry_run(tmp_path: Path) -> None:
    import hashlib
    import os
    import subprocess

    repo = Path(__file__).resolve().parents[2]
    report_path = tmp_path / "bitmex_dry_run.json"
    code_commit = "0123456789abcdef0123456789abcdef01234567"
    protected = [
        repo / "data" / "bitmex_funding_full_watermarks.json",
        repo / "research" / "sprint_004" / "39_BITMEX_FULL_BACKFILL.json",
        repo / "exp003.db",
        repo / "data" / "exp003_store",
    ]
    before = {path: _path_signature(path) for path in protected}
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo / "src")
    result = subprocess.run(
        [
            ".venv/bin/python",
            "scripts/research/backfill_bitmex_funding.py",
            "--dry-run",
            "--report-path",
            str(report_path),
            "--code-commit",
            code_commit,
            "--rate-per-minute",
            "100000",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=repo,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["data_mode"] == "synthetic"
    assert report["real_asof"] is None
    assert report["dataset_type"] == "bitmex_funding_full"
    assert set(report["symbols"]) == {
        "ETHUSD",
        "LEGACYUSD",
        "LTCUSD",
        "SOLUSDT",
        "XBTUSD",
        "XRPUSD",
    }
    assert "SPYUSD" not in report["symbols"]
    assert report["row_count"] == 600
    assert report["catalog_reconciliation"]["match"] is True
    assert report["catalog_reconciliation"]["resolve_latest_by_type"] == report["dataset_id"]
    assert report["rate_limit_incidents"] == []
    assert report["config_sha256"] != hashlib.sha256(code_commit.encode("utf-8")).hexdigest()
    assert {path: _path_signature(path) for path in protected} == before


def _raw(symbol: str, timestamp: str, rate: float, daily: float = 0.0004) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "symbol": symbol,
        "fundingInterval": "2000-01-01T08:00:00.000Z",
        "fundingRate": rate,
        "fundingRateDaily": daily,
    }


def test_subsecond_timestamp_and_unknown_availability_round_trip() -> None:
    raw = _raw("xbtusd", "2020-01-01T04:00:00.123456Z", 0.0001, 0.0005)
    norm = normalize_funding_record(raw)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    instant = datetime(2020, 1, 1, 4, 0, 0, 123456, tzinfo=timezone.utc)
    delta = instant - epoch
    expected_us = delta.days * 86_400 * 1_000_000 + delta.seconds * 1_000_000 + delta.microseconds
    assert norm["timestamp_us"] == expected_us
    assert norm["timestamp"] == "2020-01-01T04:00:00.123456Z"
    assert norm["availability_time"] is None
    assert normalize_funding_record(norm) == norm
    explicit = datetime(2020, 1, 2, tzinfo=timezone.utc)
    with_availability = normalize_funding_record(raw, availability_time=explicit)
    assert with_availability["availability_time"] != with_availability["timestamp_us"]
    drifted = dict(norm)
    drifted["timestamp_us"] = norm["timestamp_us"] + 1
    with pytest.raises(BitMEXFundingError, match="disagree"):
        normalize_funding_record(drifted)
    drifted["timestamp_us"] = True
    with pytest.raises(BitMEXFundingError, match="integer"):
        normalize_funding_record(drifted)


def test_non_finite_float_rate_is_rejected() -> None:
    with pytest.raises(BitMEXFundingError, match="non-finite"):
        normalize_funding_record(_raw("XBTUSD", "2020-01-01T04:00:00Z", float("nan")))


def test_naive_event_timestamp_is_rejected() -> None:
    with pytest.raises(BitMEXFundingError, match="timezone-aware"):
        normalize_funding_record(_raw("XBTUSD", "2020-01-01T04:00:00", 0.0001))


def test_per_symbol_all_zero_is_not_masked() -> None:
    records = [
        _raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0, 0.0),
        _raw("XBTUSD", "2020-01-01T01:00:00Z", 0.0, 0.0),
        _raw("ETHUSD", "2020-01-01T00:00:00Z", 0.0002, 0.0004),
        _raw("ETHUSD", "2020-01-01T01:00:00Z", 0.0001, 0.0004),
    ]
    with pytest.raises(BitMEXFundingError, match="all-zero nontrivial"):
        build_funding_table(records)


def test_identical_duplicates_collapse_and_conflicts_fail() -> None:
    raw = _raw("XBTUSD", "2020-01-01T04:00:00Z", 0.0001, 0.0005)
    table = build_funding_table([raw, dict(raw)])
    assert table.num_rows == 1
    conflict = _raw("XBTUSD", "2020-01-01T04:00:00Z", 0.0002, 0.0005)
    with pytest.raises(BitMEXFundingError, match="conflict"):
        build_funding_table([raw, conflict])
    normalized = normalize_funding_record(raw)
    assert len(collapse_funding_observations([normalized, dict(normalized)])) == 1


def test_request_bound_keeps_microseconds() -> None:
    bound = datetime(2020, 1, 1, 4, 0, 0, 123456, tzinfo=timezone.utc)
    assert format_funding_request_bound(bound) == "2020-01-01T04:00:00.123456Z"
    assert format_funding_request_bound(datetime(2020, 1, 1, tzinfo=timezone.utc)) == (
        "2020-01-01T00:00:00.000000Z"
    )


def test_funding_page_without_progress_is_an_error() -> None:
    page = [
        _raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001),
        _raw("XBTUSD", "2020-01-01T01:00:00Z", 0.0002),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=page)

    client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        requests_per_minute=100000,
    )
    with pytest.raises(BitMEXFundingError, match="stalled"):
        client.fetch_funding(
            "XBTUSD",
            start_time=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2020, 1, 2, tzinfo=timezone.utc),
            count=2,
        )


def test_identical_pages_collapse_and_conflicts_fail() -> None:
    first = _raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004)
    second = _raw("XBTUSD", "2020-01-01T01:00:00Z", 0.0002, 0.0004)
    third = _raw("XBTUSD", "2020-01-01T02:00:00Z", 0.0003, 0.0004)
    pages = [[first, second], [dict(first), third], []]
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        page = pages[calls["n"]] if calls["n"] < len(pages) else []
        calls["n"] += 1
        assert request.url.params["startTime"] == "2020-01-01T00:00:00.000000Z"
        return httpx.Response(200, json=page)

    client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        requests_per_minute=100000,
    )
    records = client.fetch_funding(
        "XBTUSD",
        start_time=datetime(2020, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2020, 1, 2, tzinfo=timezone.utc),
        count=2,
    )
    assert [row["timestamp"] for row in records] == [
        "2020-01-01T00:00:00Z",
        "2020-01-01T01:00:00Z",
        "2020-01-01T02:00:00Z",
    ]
    conflict_pages = [[first], [_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0009, 0.0004)]]

    def conflict_handler(request: httpx.Request) -> httpx.Response:
        index = 0 if "start=0" in str(request.url) else 1
        return httpx.Response(200, json=conflict_pages[index])

    conflict_client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(conflict_handler)),
        requests_per_minute=100000,
    )
    with pytest.raises(BitMEXFundingError, match="conflict"):
        conflict_client.fetch_funding(
            "XBTUSD",
            start_time=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2020, 1, 2, tzinfo=timezone.utc),
            count=1,
        )


def test_wrong_symbol_or_window_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_raw("ETHUSD", "2020-01-01T00:00:00Z", 0.0001)])

    client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        requests_per_minute=100000,
    )
    with pytest.raises(BitMEXFundingError, match="does not match the requested symbol"):
        client.fetch_funding("XBTUSD", start_time=datetime(2020, 1, 1, tzinfo=timezone.utc), count=1)

    def late(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_raw("XBTUSD", "2020-01-03T00:00:00Z", 0.0001)])

    late_client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(late)),
        requests_per_minute=100000,
    )
    with pytest.raises(BitMEXFundingError, match="outside the requested window"):
        late_client.fetch_funding(
            "XBTUSD",
            start_time=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2020, 1, 2, tzinfo=timezone.utc),
            count=1,
        )


def test_non_positive_page_count_is_rejected() -> None:
    client = BitMEXFundingClient(requests_per_minute=100000)
    with pytest.raises(BitMEXFundingError, match="positive integer"):
        client.fetch_funding("XBTUSD", count=0)
    with pytest.raises(BitMEXFundingError, match="positive integer"):
        client.fetch_funding("XBTUSD", count=-1)


def test_instrument_pagination_stall_is_an_error() -> None:
    page = [{"symbol": f"S{i}", "typ": "FFWCSX", "state": "Open"} for i in range(500)]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=page)

    client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        requests_per_minute=100000,
    )
    with pytest.raises(BitMEXFundingError, match="stalled"):
        client.fetch_perp_symbols(state=None, active_only=False)


def test_submicrosecond_timestamps_do_not_collapse() -> None:
    same_rate = 0.0001
    left = _raw("XBTUSD", "2020-01-01T04:00:00.1234561Z", same_rate, 0.0004)
    right = _raw("XBTUSD", "2020-01-01T04:00:00.1234562Z", same_rate, 0.0004)
    with pytest.raises(BitMEXFundingError, match="not representable"):
        build_funding_table([left, right])
    with pytest.raises(BitMEXFundingError, match="not representable"):
        normalize_funding_record(left)
    with pytest.raises(BitMEXFundingError, match="not representable"):
        normalize_funding_record(right)
    exact = normalize_funding_record(
        _raw("XBTUSD", "2020-01-01T04:00:00.123456000Z", same_rate, 0.0005)
    )
    assert exact["timestamp"] == "2020-01-01T04:00:00.123456Z"
    assert require_exact_microsecond_timestamp("2020-01-01T04:00:00.123456000Z") == (
        "2020-01-01T04:00:00.123456Z"
    )
    for stamp in (
        "2020-01-01T04:00:00,1234561Z",
        "2020-01-01T04:00:00,123456Z",
        "2020-01-01T04:00:00.123456+00:00.1234561",
        "2020-01-01T04:00:00+00:00.1",
    ):
        with pytest.raises(BitMEXFundingError, match="unsupported timestamp syntax"):
            normalize_funding_record(_raw("XBTUSD", stamp, same_rate, 0.0004))


def test_short_duplicate_funding_page_collapses() -> None:
    first = _raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004)
    second = _raw("XBTUSD", "2020-01-01T01:00:00Z", 0.0002, 0.0004)
    pages = [[first, second], [dict(first)]]
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        page = pages[calls["n"]] if calls["n"] < len(pages) else []
        calls["n"] += 1
        return httpx.Response(200, json=page)

    client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        requests_per_minute=100000,
    )
    records = client.fetch_funding(
        "XBTUSD",
        start_time=datetime(2020, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2020, 1, 2, tzinfo=timezone.utc),
        count=2,
    )
    assert calls["n"] == 2
    assert [row["timestamp"] for row in records] == [
        "2020-01-01T00:00:00Z",
        "2020-01-01T01:00:00Z",
    ]


def test_malformed_instrument_page_does_not_shrink() -> None:
    page = [{"symbol": f"S{i}", "typ": "FFWCSX", "state": "Open"} for i in range(500)]
    page[3] = ["not-a-dict"]
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(200, json=page)
        return httpx.Response(
            200,
            json=[{"symbol": "ONLYONPAGE2", "typ": "FFWCSX", "state": "Open"}],
        )

    client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        requests_per_minute=100000,
    )
    with pytest.raises(BitMEXFundingError, match="malformed instrument"):
        client.fetch_perp_symbols(state=None, active_only=False)
    assert calls["n"] == 1


def test_instrument_fields_fail_closed_and_non_perps_stay_filterable() -> None:
    def numeric_symbol(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{"symbol": 123, "typ": "FFWCSX", "state": "Open"}],
        )

    client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(numeric_symbol)),
        requests_per_minute=100000,
    )
    with pytest.raises(BitMEXFundingError, match="malformed instrument"):
        client.fetch_perp_symbols()

    def missing_state(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"symbol": "XBTUSD", "typ": "FFWCSX"}])

    state_client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(missing_state)),
        requests_per_minute=100000,
    )
    with pytest.raises(BitMEXFundingError, match="malformed instrument"):
        state_client.fetch_perp_symbols(state="Open")
    assert state_client.fetch_perp_symbols(state=None) == ["XBTUSD"]

    def mixed_types(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {"symbol": "SPYUSD", "typ": "FFCCSX", "state": "Open"},
                {"symbol": "XBTUSD", "typ": "FFWCSX", "state": "Open"},
                {"symbol": "", "typ": "FFWCSX", "state": "Open"},
            ],
        )

    mixed_client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(mixed_types)),
        requests_per_minute=100000,
    )
    with pytest.raises(BitMEXFundingError, match="malformed instrument"):
        mixed_client.fetch_perp_symbols()

    def non_perp(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {"symbol": "SPYUSD", "typ": "FFCCSX", "state": "Open"},
                {"symbol": "XBTUSD", "typ": "FFWCSX", "state": "Open"},
            ],
        )

    filter_client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(non_perp)),
        requests_per_minute=100000,
    )
    assert filter_client.fetch_perp_symbols() == ["XBTUSD"]


def test_short_duplicate_instrument_page_collapses() -> None:
    first = [{"symbol": f"S{i}", "typ": "FFWCSX", "state": "Open"} for i in range(500)]
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(200, json=first)
        if calls["n"] == 2:
            return httpx.Response(200, json=[dict(first[0])])
        return httpx.Response(200, json=[])

    client = BitMEXFundingClient(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        requests_per_minute=100000,
    )
    symbols = client.fetch_perp_symbols(state=None, active_only=False)
    assert calls["n"] == 2
    assert len(symbols) == 500
    assert "S0" in symbols
    assert "S499" in symbols

