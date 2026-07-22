"""ASOF-001 — focused integration tests for the approved as-of access API.

Contract surface tested:
- ``observation_eligible`` / ``reference_eligible`` rules
- ``CatalogAsOfStore.latest_available`` / ``as_of`` on
  ``ref_instrument_version`` (REF-001), ``ref_fee_schedule`` (FEE-001),
  and a ``market_bars`` dataset (BAR-001)
- bitemporal boundaries, ``max_age``, empty results, error cases
- factor-path smoke: the as-of contract is importable so factor code uses it
  instead of reimplementing temporal joins

Source under test is the approved drop (``cryptofactors.catalog.as_of``); it is
not modified here. Tests construct their own temporary control DB + dataset tree
so they require no production data and no network.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import sqlite3

from cryptofactors.catalog.as_of import (
    AsOfAccessError,
    CatalogAsOfStore,
    observation_eligible,
    reference_eligible,
)
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(s: str) -> str:
    return s + "Z" if not s.endswith("Z") else s


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(_iso(s)).astimezone(UTC)


def _us(s: str) -> int:
    return int(_ts(s).timestamp() * 1_000_000)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def control_db(tmp_path: Path) -> Path:
    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys = ON")
    # Parent rows required by FK constraints.
    conn.execute(
        "INSERT INTO ref_venue (venue_id, venue_code, display_name, venue_type, created_at) "
        "VALUES ('V1','V1','Venue One','CEX','2020-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO ref_asset (asset_id, asset_class, display_name, created_at) "
        "VALUES ('A1','CRYPTO','Asset One','2020-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO ref_asset (asset_id, asset_class, display_name, created_at) "
        "VALUES ('A2','CRYPTO','Asset Two','2020-01-01T00:00:00Z')"
    )
    # Instruments referencing the assets/venue.
    conn.execute(
        "INSERT INTO ref_instrument (instrument_id, asset_id, venue_id, "
        "instrument_type, created_at) VALUES ('INST1','A1','V1','PERPETUAL','2020-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO ref_instrument (instrument_id, asset_id, venue_id, "
        "instrument_type, created_at) VALUES ('INST2','A2','V1','PERPETUAL','2020-01-01T00:00:00Z')"
    )
    # ref_instrument_version: INST1 has two overlapping valid windows.
    conn.execute(
        "INSERT INTO ref_instrument_version VALUES ("
        "'IV1','INST1',1,'{\"x\":1}',"
        "'2021-01-01T00:00:00Z','2021-06-01T00:00:00Z',"
        "'2021-01-01T00:00:00Z','2021-12-01T00:00:00Z',NULL,'{\"e\":1}')"
    )
    conn.execute(
        "INSERT INTO ref_instrument_version VALUES ("
        "'IV2','INST1',2,'{\"x\":2}',"
        "'2021-06-01T00:00:00Z','2022-01-01T00:00:00Z',"
        "'2021-01-01T00:00:00Z','2021-12-01T00:00:00Z',NULL,'{\"e\":2}')"
    )
    # ref_fee_schedule: INST1 maker/taker across two valid windows.
    conn.execute(
        "INSERT INTO ref_fee_schedule VALUES ("
        "'FS1','INST1','TIER1','0.001','0.002','OFFICIAL_SCHEDULE',"
        "'2021-01-01T00:00:00Z','2021-06-01T00:00:00Z',"
        "'2021-01-01T00:00:00Z','2021-12-01T00:00:00Z',NULL,'{\"e\":1}')"
    )
    conn.execute(
        "INSERT INTO ref_fee_schedule VALUES ("
        "'FS2','INST1','TIER1','0.0005','0.001','OFFICIAL_SCHEDULE',"
        "'2021-06-01T00:00:00Z','2022-01-01T00:00:00Z',"
        "'2021-01-01T00:00:00Z','2021-12-01T00:00:00Z',NULL,'{\"e\":2}')"
    )
    conn.commit()
    conn.close()
    return db


@pytest.fixture()
def bars_root(tmp_path: Path, control_db: Path) -> Path:
    root = tmp_path / "datasets"
    ds_dir = root / "market_bars" / "ds_bars"
    ds_dir.mkdir(parents=True)
    table = pa.table(
        {
            "instrument_id": pa.array([1, 1, 2], pa.int64()),
            "venue_id": pa.array(["V1", "V1", "V1"], pa.string()),
            "timeframe": pa.array(["1d", "1d", "1d"], pa.string()),
            "period_start": pa.array(
                [_us("2021-03-01T00:00:00Z"), _us("2021-09-01T00:00:00Z"), _us("2021-03-01T00:00:00Z")],
                pa.int64(),
            ),
            "period_end": pa.array(
                [_us("2021-12-31T00:00:00Z"), _us("2021-12-31T00:00:00Z"), _us("2021-12-31T00:00:00Z")],
                pa.int64(),
            ),
            "availability_time": pa.array(
                [_us("2021-03-01T01:00:00Z"), _us("2021-09-01T01:00:00Z"), _us("2021-03-01T01:00:00Z")],
                pa.int64(),
            ),
            "open": pa.array([1.0, 2.0, 9.0], pa.float64()),
            "high": pa.array([1.1, 2.1, 9.1], pa.float64()),
            "low": pa.array([0.9, 1.9, 8.9], pa.float64()),
            "close": pa.array([1.0, 2.0, 9.0], pa.float64()),
            "base_volume": pa.array([10.0, 20.0, 5.0], pa.float64()),
            "quote_volume": pa.array([10.0, 20.0, 5.0], pa.float64()),
            "source_dataset_id": pa.array(["ds_bars", "ds_bars", "ds_bars"], pa.string()),
            "quality_flags": pa.array([[], [], []], pa.list_(pa.string())),
        }
    )
    pq.write_table(table, ds_dir / "part-0.parquet")

    conn = sqlite3.connect(str(control_db))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT INTO dataset (dataset_id, dataset_type, schema_version, "
        "manifest_sha256, manifest_uri, publication_uri, transform_name, "
        "transform_version, code_commit, config_sha256, row_count, byte_size, "
        "event_start, event_end, availability_start, availability_end, "
        "quality_status, publication_status, created_at) VALUES ("
        "'ds_bars','market_bars','1','sha256:bars','m.json','p.json','bar',"
        "'1','abc','cfg',3,123,'2021-03-01T00:00:00Z','2021-09-02T00:00:00Z',"
        "'2021-03-01T01:00:00Z','2021-09-01T01:00:00Z','ACCEPTED','REGISTERED',"
        "'2021-03-01T01:00:00Z')"
    )
    conn.execute(
        "INSERT INTO dataset_file (dataset_id, storage_uri, file_sha256, "
        "row_count, byte_size) VALUES ('ds_bars','market_bars/ds_bars/part-0.parquet',"
        "'sha256:part','3','123')"
    )
    conn.commit()
    conn.close()
    return root


@pytest.fixture()
def store(control_db: Path, bars_root: Path) -> CatalogAsOfStore:
    return CatalogAsOfStore(control_database=control_db, dataset_store_root=bars_root)


# ---------------------------------------------------------------------------
# Eligibility rules
# ---------------------------------------------------------------------------

def test_observation_eligible_requires_availability() -> None:
    assert observation_eligible(decision_time_us=_us("2021-05-01T00:00:00Z"), availability_time_us=None) is False


def test_observation_eligible_future_availability_rejected() -> None:
    t = _us("2021-05-01T00:00:00Z")
    future = _us("2021-06-01T00:00:00Z")
    assert observation_eligible(decision_time_us=t, availability_time_us=future) is False


def test_observation_eligible_valid_window_half_open() -> None:
    t = _us("2021-05-01T00:00:00Z")
    ok = observation_eligible(
        decision_time_us=t,
        availability_time_us=_us("2021-04-01T00:00:00Z"),
        valid_from_us=_us("2021-03-01T00:00:00Z"),
        valid_to_us=_us("2021-06-01T00:00:00Z"),
    )
    assert ok is True
    bad = observation_eligible(
        decision_time_us=_us("2021-06-01T00:00:00Z"),
        availability_time_us=_us("2021-04-01T00:00:00Z"),
        valid_from_us=_us("2021-03-01T00:00:00Z"),
        valid_to_us=_us("2021-06-01T00:00:00Z"),
    )
    assert bad is False


def test_reference_eligible_valid_and_known_windows() -> None:
    ok = reference_eligible(
        decision_time_us=_us("2021-05-01T00:00:00Z"),
        knowledge_time_us=_us("2021-05-01T00:00:00Z"),
        valid_from_us=_us("2021-03-01T00:00:00Z"),
        valid_to_us=_us("2021-06-01T00:00:00Z"),
        known_from_us=_us("2021-01-01T00:00:00Z"),
        known_to_us=_us("2021-12-01T00:00:00Z"),
    )
    assert ok is True


def test_reference_eligible_known_after_knowledge_time_rejected() -> None:
    ok = reference_eligible(
        decision_time_us=_us("2021-05-01T00:00:00Z"),
        knowledge_time_us=_us("2020-01-01T00:00:00Z"),
        valid_from_us=_us("2021-03-01T00:00:00Z"),
        valid_to_us=_us("2021-06-01T00:00:00Z"),
        known_from_us=_us("2021-01-01T00:00:00Z"),
        known_to_us=_us("2021-12-01T00:00:00Z"),
    )
    assert ok is False


# ---------------------------------------------------------------------------
# market_bars
# ---------------------------------------------------------------------------

def test_market_bars_latest_available_picks_newest_period(store: CatalogAsOfStore) -> None:
    t = _ts("2021-10-01T00:00:00Z")
    tbl = store.latest_available("ds_bars", keys=[1], fields=["instrument_id", "close"], decision_time=t)
    assert tbl.num_rows == 1
    row = tbl.to_pylist()[0]
    assert row["instrument_id"] == 1
    assert row["close"] == 2.0


def test_market_bars_latest_available_respects_decision_time(store: CatalogAsOfStore) -> None:
    t = _ts("2021-08-01T00:00:00Z")
    tbl = store.latest_available("ds_bars", keys=[1], fields=["close"], decision_time=t)
    assert tbl.num_rows == 1
    assert tbl.to_pylist()[0]["close"] == 1.0


def test_market_bars_as_of_returns_all_eligible(store: CatalogAsOfStore) -> None:
    t = _ts("2021-10-01T00:00:00Z")
    tbl = store.as_of("ds_bars", keys=[1], fields=["period_start"], decision_time=t)
    assert tbl.num_rows == 2


def test_market_bars_missing_key_returns_empty(store: CatalogAsOfStore) -> None:
    t = _ts("2021-10-01T00:00:00Z")
    tbl = store.latest_available("ds_bars", keys=[999], fields=["close"], decision_time=t)
    assert tbl.num_rows == 0


def test_market_bars_max_age_filters_old_availability(store: CatalogAsOfStore) -> None:
    t = _ts("2021-10-01T00:00:00Z")
    tbl = store.latest_available(
        "ds_bars", keys=[1], fields=["close"], decision_time=t, max_age=timedelta(days=60)
    )
    assert tbl.num_rows == 1
    assert tbl.to_pylist()[0]["close"] == 2.0


# ---------------------------------------------------------------------------
# fee schedule
# ---------------------------------------------------------------------------

def test_fee_schedule_latest_available_after_window(store: CatalogAsOfStore) -> None:
    t = _ts("2021-08-01T00:00:00Z")
    tbl = store.latest_available(
        "ref_fee_schedule", keys=["INST1"], fields=["maker_fee_rate"], decision_time=t
    )
    assert tbl.num_rows == 1
    assert tbl.to_pylist()[0]["maker_fee_rate"] == "0.0005"


def test_fee_schedule_before_first_window_empty(store: CatalogAsOfStore) -> None:
    t = _ts("2020-01-01T00:00:00Z")
    tbl = store.latest_available("ref_fee_schedule", keys=["INST1"], fields=["maker_fee_rate"], decision_time=t)
    assert tbl.num_rows == 0


def test_fee_schedule_as_of_known_after_knowledge_empty(store: CatalogAsOfStore) -> None:
    t = _ts("2021-08-01T00:00:00Z")
    k = _ts("2022-06-01T00:00:00Z")
    tbl = store.as_of("ref_fee_schedule", keys=["INST1"], fields=["maker_fee_rate"], decision_time=t, knowledge_time=k)
    assert tbl.num_rows == 0


# ---------------------------------------------------------------------------
# instrument version
# ---------------------------------------------------------------------------

def test_instrument_version_latest_picks_higher_version_seq(store: CatalogAsOfStore) -> None:
    t = _ts("2021-08-01T00:00:00Z")
    tbl = store.latest_available(
        "ref_instrument_version", keys=["INST1"], fields=["version_seq"], decision_time=t
    )
    assert tbl.num_rows == 1
    assert tbl.to_pylist()[0]["version_seq"] == 2


def test_instrument_version_as_of_returns_eligible(store: CatalogAsOfStore) -> None:
    t = _ts("2021-08-01T00:00:00Z")
    tbl = store.as_of("ref_instrument_version", keys=["INST1"], fields=["instrument_version_id"], decision_time=t)
    assert tbl.num_rows == 1
    assert tbl.to_pylist()[0]["instrument_version_id"] == "IV2"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_unsupported_dataset_raises(store: CatalogAsOfStore) -> None:
    with pytest.raises(AsOfAccessError):
        store.latest_available("totally_unknown_ds", keys=[1], fields=["x"], decision_time=_ts("2021-08-01T00:00:00Z"))


def test_market_bars_without_root_raises(control_db: Path) -> None:
    # Register the dataset so resolution succeeds, then omit the store root to
    # reach the root-required check.
    conn = sqlite3.connect(str(control_db))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT OR IGNORE INTO dataset (dataset_id, dataset_type, schema_version, "
        "manifest_sha256, manifest_uri, publication_uri, transform_name, "
        "transform_version, code_commit, config_sha256, row_count, byte_size, "
        "event_start, event_end, availability_start, availability_end, "
        "quality_status, publication_status, created_at) VALUES ("
        "'ds_bars','market_bars','1','sha256:bars','m.json','p.json','bar',"
        "'1','abc','cfg',3,123,'2021-03-01T00:00:00Z','2021-09-02T00:00:00Z',"
        "'2021-03-01T01:00:00Z','2021-09-01T01:00:00Z','ACCEPTED','REGISTERED',"
        "'2021-03-01T01:00:00Z')"
    )
    conn.commit()
    conn.close()
    st = CatalogAsOfStore(control_database=control_db, dataset_store_root=None)
    with pytest.raises(AsOfAccessError, match="dataset_store_root"):
        st.latest_available("ds_bars", keys=[1], fields=["close"], decision_time=_ts("2021-08-01T00:00:00Z"))


def test_naive_decision_time_raises(store: CatalogAsOfStore) -> None:
    with pytest.raises(AsOfAccessError):
        store.latest_available(
            "ref_fee_schedule", keys=["INST1"], fields=["maker_fee_rate"],
            decision_time=datetime(2021, 8, 1),
        )


def test_negative_max_age_raises(store: CatalogAsOfStore) -> None:
    with pytest.raises(AsOfAccessError, match="max_age"):
        store.latest_available(
            "ds_bars", keys=[1], fields=["close"],
            decision_time=_ts("2021-08-01T00:00:00Z"), max_age=timedelta(days=-1),
        )


def test_requested_field_not_present_raises(store: CatalogAsOfStore) -> None:
    with pytest.raises(AsOfAccessError, match="not present"):
        store.latest_available(
            "ref_fee_schedule", keys=["INST1"], fields=["nonexistent_col"],
            decision_time=_ts("2021-08-01T00:00:00Z"),
        )


def test_empty_key_list_returns_empty_fee(store: CatalogAsOfStore) -> None:
    tbl = store.latest_available("ref_fee_schedule", keys=[], fields=["maker_fee_rate"], decision_time=_ts("2021-08-01T00:00:00Z"))
    assert tbl.num_rows == 0


# ---------------------------------------------------------------------------
# Factor-path smoke: as-of contract is importable; factor code must use it.
# ---------------------------------------------------------------------------

def test_as_of_store_is_importable_from_catalog_package() -> None:
    from cryptofactors.catalog import CatalogAsOfStore as C
    from cryptofactors.catalog import AsOfStore as P

    assert C is CatalogAsOfStore
    assert P is not None
