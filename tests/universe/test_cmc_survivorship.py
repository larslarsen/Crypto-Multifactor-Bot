"""Tests for UNIVERSE-003 CoinMarketCap survivorship registry and provider."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from typing import Any

import pyarrow.parquet as pq
import pytest

from cryptofactors.universe import (
    PROVENANCE_SOURCE,
    CMCSurvivorshipError,
    CMCSurvivorshipProvider,
    build_cmc_survivorship_table,
    normalize_coin_record,
)


def sample_raw_coins() -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    map_coins = [
        {
            "id": 7,
            "name": "Devcoin",
            "symbol": "DVC",
            "slug": "devcoin",
            "is_active": 0,
        },
        {
            "id": 12,
            "name": "Bytecoin",
            "symbol": "BYTE",
            "slug": "bytecoin",
            "is_active": 0,
        },
    ]
    details = {
        7: {
            "id": 7,
            "name": "Devcoin",
            "symbol": "DVC",
            "dateLaunched": "2011-07-22T00:00:00.000Z",
            "dateAdded": "2013-04-28T00:00:00.000Z",
            "latestUpdateTime": "2017-11-23T00:00:00.000Z",
            "status": "inactive",
        },
        12: {
            "id": 12,
            "name": "Bytecoin",
            "symbol": "BYTE",
            "dateLaunched": "2012-05-01T00:00:00.000Z",
            "dateAdded": "2013-05-01T00:00:00.000Z",
            "latestUpdateTime": "2019-01-01T00:00:00.000Z",
            "status": "inactive",
        },
    }
    return map_coins, details


def test_provenance_labels_present_on_every_row() -> None:
    map_coins, details = sample_raw_coins()
    records = []
    for m in map_coins:
        d = details[int(m["id"])]
        records.append(normalize_coin_record(m, d))

    provider = CMCSurvivorshipProvider.from_records(records)
    rows = provider.records()

    assert len(rows) == 2
    for row in rows:
        assert "death_date_is_proxy" in row
        assert row["death_date_is_proxy"] is True
        assert "source" in row
        assert row["source"] == PROVENANCE_SOURCE
        assert row["source"] == "cmc_data_api_unofficial"


def test_normalize_coin_record_validation() -> None:
    with pytest.raises(CMCSurvivorshipError, match="missing required 'id'"):
        normalize_coin_record({"symbol": "FOO", "name": "FooCoin"})

    with pytest.raises(CMCSurvivorshipError, match="missing required symbol"):
        normalize_coin_record({"id": 1, "name": "FooCoin"})

    with pytest.raises(CMCSurvivorshipError, match="missing required name"):
        normalize_coin_record({"id": 1, "symbol": "FOO"})


def test_point_in_time_membership_universe_at() -> None:
    map_coins, details = sample_raw_coins()
    records = [normalize_coin_record(m, details[int(m["id"])]) for m in map_coins]
    provider = CMCSurvivorshipProvider.from_records(records)

    # Decision time before Devcoin birth (2013-04-28)
    t_before = datetime(2012, 1, 1, tzinfo=timezone.utc)
    univ_before = provider.universe_at(t_before)
    assert "cmc_7" not in univ_before

    # Decision time during Devcoin active life (2015-01-01)
    t_active = datetime(2015, 1, 1, tzinfo=timezone.utc)
    univ_active = provider.universe_at(t_active)
    assert "cmc_7" in univ_active
    assert "cmc_12" in univ_active

    # Decision time after Devcoin death proxy (2017-11-23)
    t_after = datetime(2018, 6, 1, tzinfo=timezone.utc)
    univ_after = provider.universe_at(t_after)
    assert "cmc_7" not in univ_after
    assert "cmc_12" in univ_after  # Bytecoin still alive in mid 2018


def test_csv_and_parquet_io() -> None:
    map_coins, details = sample_raw_coins()
    records = [normalize_coin_record(m, details[int(m["id"])]) for m in map_coins]
    table = build_cmc_survivorship_table(records)

    with tempfile.TemporaryDirectory() as tmpdir:
        pq_path = Path(tmpdir) / "cmc.parquet"
        pq.write_table(table, str(pq_path))

        provider_pq = CMCSurvivorshipProvider.from_parquet(pq_path)
        assert len(provider_pq.records()) == 2
        for r in provider_pq.records():
            assert r["death_date_is_proxy"] is True
            assert r["source"] == "cmc_data_api_unofficial"


def test_empty_records_fails_closed() -> None:
    with pytest.raises(CMCSurvivorshipError, match="cannot build registry table from empty records"):
        build_cmc_survivorship_table([])
