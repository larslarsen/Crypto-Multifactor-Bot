"""BASE-001 — transparent baseline factors (momentum, mean-reversion, volume).

Unit tests use a timestamp-aware fake as-of store. Substrate integration builds
a real CatalogAsOfStore + synthetic market_bars Parquet and runs each baseline
through LABEL → SPLIT → EXP (same pattern as NULL-001).
"""

from __future__ import annotations

import math
import shutil
import sqlite3
import statistics
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.catalog.as_of import CatalogAsOfStore
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations
from cryptofactors.factors.baseline import (
    BASELINE_FACTOR_ORDER,
    DEFAULT_WINDOW,
    BaselineFactorError,
    MeanReversionFactor,
    MomentumFactor,
    VolumeFactor,
)
from cryptofactors.factors.contract import Factor, FactorFrame
from cryptofactors.validation.experiment import (
    ExperimentBundle,
    InMemoryExperimentRegistry,
)
from cryptofactors.validation.labels import (
    AsOfLabelEngine,
    LabelConfig,
    LabelType,
)
from cryptofactors.validation.split import (
    PurgedChronologicalSplitter,
    SplitConfig,
    SplitMode,
)

UTC = timezone.utc
_DATASET = "ds_baseline_bars"
_INSTRUMENT_DATASET_ID = "ref_instrument_version"
_US = 1_000_000


def _ts(day: int) -> datetime:
    return datetime(2020, 1, 1, tzinfo=UTC) + timedelta(days=day)


def _us(dt: datetime) -> int:
    return int(dt.astimezone(UTC).timestamp() * _US)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class _FakeAsOf:
    """As-of fake with production BAR-001 timestamps.

    Input series keys are bar ``period_start`` times. Each bar is modeled as:
    ``period_end = period_start + 1d``, ``availability_time = period_end``
    (same as ``market/bars.py``).
    """

    def __init__(
        self,
        prices: dict[str, list[tuple[datetime, float]]],
        volumes: dict[str, list[tuple[datetime, float]]] | None = None,
    ) -> None:
        self._prices = {
            k: sorted(((t.astimezone(UTC), float(p)) for t, p in v), key=lambda x: x[0])
            for k, v in prices.items()
        }
        vols = volumes if volumes is not None else {}
        self._volumes = {
            k: sorted(((t.astimezone(UTC), float(p)) for t, p in v), key=lambda x: x[0])
            for k, v in vols.items()
        }

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> pa.Table:
        del dataset_id, max_age
        empty = pa.table(
            {
                "instrument_id": pa.array([], pa.string()),
                "close": pa.array([], pa.float64()),
                "base_volume": pa.array([], pa.float64()),
                "availability_time": pa.array([], pa.int64()),
                "period_start": pa.array([], pa.int64()),
            }
        )
        if not keys:
            return empty
        inst = str(keys[0])
        d = decision_time.astimezone(UTC)
        close_hit = self._pick_available(self._prices.get(inst, []), d)
        vol_hit = self._pick_available(self._volumes.get(inst, []), d)

        want_close = "close" in fields
        want_vol = "base_volume" in fields
        if want_close and close_hit is None:
            return empty
        if want_vol and not want_close and vol_hit is None:
            return empty
        if want_vol and vol_hit is None and close_hit is not None:
            return empty

        if close_hit is not None:
            period_start, close_v = close_hit
        else:
            assert vol_hit is not None
            period_start, _ = vol_hit
            close_v = None
        vol_v = self._value_at(self._volumes.get(inst, []), period_start)
        period_end = period_start + timedelta(days=1)
        avail_us = _us(period_end)
        pstart_us = _us(period_start)
        data: dict[str, object] = {
            "instrument_id": pa.array([inst], pa.string()),
            "availability_time": pa.array([avail_us], pa.int64()),
            "period_start": pa.array([pstart_us], pa.int64()),
        }
        if close_v is not None:
            data["close"] = pa.array([close_v], pa.float64())
        if vol_v is not None:
            data["base_volume"] = pa.array([vol_v], pa.float64())
        names = [f for f in fields if f in data] or list(data.keys())
        return pa.table({n: data[n] for n in names})

    @staticmethod
    def _pick_available(
        series: list[tuple[datetime, float]], as_of: datetime
    ) -> tuple[datetime, float] | None:
        """Latest bar with availability_time (= period_start+1d) <= as_of."""
        chosen: tuple[datetime, float] | None = None
        for period_start, v in series:
            availability = period_start + timedelta(days=1)
            if availability <= as_of:
                chosen = (period_start, v)
            else:
                break
        return chosen

    @staticmethod
    def _value_at(
        series: list[tuple[datetime, float]], period_start: datetime
    ) -> float | None:
        for tt, v in series:
            if tt == period_start:
                return v
        return None


def _flat_history(
    instrument_id: str,
    *,
    days: int,
    price: float,
    volume: float = 1000.0,
) -> tuple[
    dict[str, list[tuple[datetime, float]]],
    dict[str, list[tuple[datetime, float]]],
]:
    prices = [(_ts(d), price) for d in range(days)]
    volumes = [(_ts(d), volume) for d in range(days)]
    return {instrument_id: prices}, {instrument_id: volumes}


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_baseline_factor_order_preregistered() -> None:
    assert BASELINE_FACTOR_ORDER == ("momentum", "mean_reversion", "volume")


def test_momentum_implements_factor_protocol() -> None:
    prices, volumes = _flat_history("1", days=40, price=100.0)
    store = _FakeAsOf(prices, volumes)
    factor = MomentumFactor(store, market_dataset_id=_DATASET, window=20)
    assert isinstance(factor, Factor)
    assert factor.factor_id == "momentum"
    assert factor.window == DEFAULT_WINDOW


def test_momentum_trailing_return_deterministic() -> None:
    prices: dict[str, list[tuple[datetime, float]]] = {
        "1": [(_ts(d), 100.0 + d) for d in range(40)],
        "2": [(_ts(d), 200.0) for d in range(40)],
    }
    store = _FakeAsOf(prices)
    factor = MomentumFactor(store, market_dataset_id=_DATASET, window=20)
    # Bar period_start day 30 is available at day 31 (availability=period_end).
    as_of = _ts(31)
    a = factor.compute(("2", "1"), as_of)
    b = factor.compute(("1", "2"), as_of)
    assert isinstance(a, FactorFrame)
    assert [v.instrument_id for v in a.values] == ["1", "2"]
    assert [v.score for v in a.values] == [v.score for v in b.values]
    # window=20 → 21 distinct bars day 10..30: 110 → 130
    m1 = next(v for v in a.values if v.instrument_id == "1")
    assert m1.score == pytest.approx((130.0 / 110.0) - 1.0)
    m2 = next(v for v in a.values if v.instrument_id == "2")
    assert m2.score == pytest.approx(0.0)


def test_history_uses_distinct_observations_across_gaps() -> None:
    """Sparse bars: distinct walk via availability_time must not duplicate."""
    prices = {"1": [(_ts(d), 100.0 + d) for d in range(0, 33, 3)]}
    store = _FakeAsOf(prices)
    factor = MeanReversionFactor(store, market_dataset_id=_DATASET, window=5)
    # Day-30 bar available at day 31.
    frame = factor.compute(("1",), _ts(31))
    assert len(frame.values) == 1
    series = [118.0, 121.0, 124.0, 127.0, 130.0]
    mean = statistics.fmean(series)
    stdev = statistics.pstdev(series)
    z = (130.0 - mean) / stdev
    assert frame.values[0].raw_value == pytest.approx(z)
    assert frame.values[0].score == pytest.approx(-z)


def test_mean_reversion_negative_z_when_elevated() -> None:
    series = [(_ts(d), 100.0) for d in range(19)] + [(_ts(19), 130.0)]
    store = _FakeAsOf({"1": series})
    factor = MeanReversionFactor(store, market_dataset_id=_DATASET, window=20)
    frame = factor.compute(("1",), _ts(20))
    assert frame.values[0].raw_value > 0.0
    assert frame.values[0].score < 0.0
    assert frame.values[0].score == pytest.approx(-frame.values[0].raw_value)


def test_volume_ratio_elevated_current() -> None:
    vols = [(_ts(d), 100.0) for d in range(19)] + [(_ts(19), 300.0)]
    prices = [(_ts(d), 50.0) for d in range(20)]
    store = _FakeAsOf({"1": prices}, {"1": vols})
    factor = VolumeFactor(store, market_dataset_id=_DATASET, window=20)
    frame = factor.compute(("1",), _ts(20))
    assert frame.values[0].score == pytest.approx(300.0 / 110.0)


def test_rejects_negative_price() -> None:
    prices = {"1": [(_ts(d), -1.0 if d == 10 else 10.0) for d in range(20)]}
    store = _FakeAsOf(prices)
    factor = MomentumFactor(store, market_dataset_id=_DATASET, window=5)
    with pytest.raises(BaselineFactorError, match="must be > 0"):
        factor.compute(("1",), _ts(16))


def test_rejects_negative_volume() -> None:
    prices = {"1": [(_ts(d), 10.0) for d in range(20)]}
    vols = {"1": [(_ts(d), -5.0 if d == 15 else 100.0) for d in range(20)]}
    store = _FakeAsOf(prices, vols)
    factor = VolumeFactor(store, market_dataset_id=_DATASET, window=5)
    with pytest.raises(BaselineFactorError, match="must be >= 0"):
        factor.compute(("1",), _ts(16))


def test_rejects_string_universe() -> None:
    prices, volumes = _flat_history("1", days=30, price=10.0)
    store = _FakeAsOf(prices, volumes)
    factor = MomentumFactor(store, market_dataset_id=_DATASET, window=5)
    with pytest.raises(BaselineFactorError, match="not str/bytes"):
        factor.compute("1", _ts(21))


def test_rejects_naive_as_of_and_empty_universe() -> None:
    prices, volumes = _flat_history("1", days=30, price=10.0)
    store = _FakeAsOf(prices, volumes)
    factor = MomentumFactor(store, market_dataset_id=_DATASET, window=5)
    with pytest.raises(BaselineFactorError):
        factor.compute((), _ts(21))
    with pytest.raises(BaselineFactorError):
        factor.compute(("1",), datetime(2020, 1, 20))


def test_insufficient_history_fail_closed() -> None:
    prices = {"1": [(_ts(0), 10.0)]}
    store = _FakeAsOf(prices)
    factor = MomentumFactor(store, market_dataset_id=_DATASET, window=20)
    with pytest.raises(BaselineFactorError, match="insufficient"):
        factor.compute(("1",), _ts(5))


def test_zero_stdev_mean_reversion_fail_closed() -> None:
    prices, _ = _flat_history("1", days=30, price=42.0)
    store = _FakeAsOf(prices)
    factor = MeanReversionFactor(store, market_dataset_id=_DATASET, window=10)
    with pytest.raises(BaselineFactorError, match="stdev is zero"):
        factor.compute(("1",), _ts(21))


def test_window_validation() -> None:
    prices, volumes = _flat_history("1", days=10, price=1.0)
    store = _FakeAsOf(prices, volumes)
    with pytest.raises(BaselineFactorError, match="window"):
        MomentumFactor(store, market_dataset_id=_DATASET, window=1)
    with pytest.raises(BaselineFactorError):
        MomentumFactor(store, market_dataset_id="")


def test_all_baselines_are_factors() -> None:
    prices: dict[str, list[tuple[datetime, float]]] = {
        "1": [(_ts(d), 100.0 + 0.5 * d) for d in range(40)],
        "2": [(_ts(d), 80.0 + d) for d in range(40)],
    }
    volumes: dict[str, list[tuple[datetime, float]]] = {
        "1": [(_ts(d), 1000.0 + d) for d in range(40)],
        "2": [(_ts(d), 500.0 + 2 * d) for d in range(40)],
    }
    store = _FakeAsOf(prices, volumes)
    factors: list[Factor] = [
        MomentumFactor(store, market_dataset_id=_DATASET, window=20),
        MeanReversionFactor(store, market_dataset_id=_DATASET, window=20),
        VolumeFactor(store, market_dataset_id=_DATASET, window=20),
    ]
    as_of = _ts(31)
    for factor in factors:
        assert isinstance(factor, Factor)
        frame = factor.compute(("2", "1"), as_of)
        assert frame.factor_id in BASELINE_FACTOR_ORDER
        assert len(frame.values) == 2
        assert all(math.isfinite(v.score) for v in frame.values)


# ---------------------------------------------------------------------------
# Substrate integration (CatalogAsOfStore → LABEL → SPLIT → EXP)
# ---------------------------------------------------------------------------


def _build_catalog_asof(
    root: Path,
    *,
    instruments: list[int],
    start: datetime,
    n_days: int,
    price_seed: int,
    market_dataset_id: str = _DATASET,
) -> CatalogAsOfStore:
    db = root / "control.db"
    store_root = root / "datasets"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys = ON")
    created = _iso(start - timedelta(days=1))
    valid_from = _iso(start - timedelta(days=1))
    valid_to = _iso(start + timedelta(days=n_days + 30))
    conn.execute(
        "INSERT INTO ref_venue (venue_id, venue_code, display_name, venue_type, created_at) "
        "VALUES ('V1','V1','Venue One','CEX',?)",
        (created,),
    )
    for iid in instruments:
        aid = f"A{iid}"
        conn.execute(
            "INSERT INTO ref_asset (asset_id, asset_class, display_name, created_at) "
            "VALUES (?,?,?,?)",
            (aid, "CRYPTO", f"Asset {iid}", created),
        )
        conn.execute(
            "INSERT INTO ref_instrument (instrument_id, asset_id, venue_id, "
            "instrument_type, base_asset_id, quote_asset_id, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (str(iid), aid, "V1", "PERPETUAL", aid, aid, created),
        )
        conn.execute(
            "INSERT INTO ref_instrument_version ("
            "instrument_version_id, instrument_id, version_seq, contract_spec_json, "
            "valid_from, valid_to, known_from, known_to, supersedes_version_id, evidence_json"
            ") VALUES (?,?,?,?,?,?,?,?,NULL,?)",
            (
                f"IV{iid}",
                str(iid),
                1,
                "{}",
                valid_from,
                valid_to,
                valid_from,
                valid_to,
                "{}",
            ),
        )

    rng = Random(price_seed)
    n_rows = 0
    inst_col: list[int] = []
    venue_col: list[str] = []
    tf_col: list[str] = []
    pstart_col: list[int] = []
    pend_col: list[int] = []
    avail_col: list[int] = []
    open_col: list[float] = []
    high_col: list[float] = []
    low_col: list[float] = []
    close_col: list[float] = []
    base_vol_col: list[float] = []
    quote_vol_col: list[float] = []
    src_col: list[str] = []
    flags_col: list[list[str]] = []
    for iid in instruments:
        for day in range(n_days + 5):
            ts = start + timedelta(days=day)
            period_end = ts + timedelta(days=1)
            # Production BAR-001: availability_time = period_end (bars.py).
            close = float(math.exp(rng.gauss(4.6, 0.15)))
            vol = float(abs(rng.gauss(1000.0, 50.0)) + 10.0)
            inst_col.append(int(iid))
            venue_col.append("V1")
            tf_col.append("1d")
            pstart_col.append(_us(ts))
            pend_col.append(_us(period_end))
            avail_col.append(_us(period_end))
            open_col.append(close)
            high_col.append(close * 1.01)
            low_col.append(close * 0.99)
            close_col.append(close)
            base_vol_col.append(vol)
            quote_vol_col.append(vol * close)
            src_col.append(market_dataset_id)
            flags_col.append([])
            n_rows += 1

    ds_dir = store_root / "market_bars" / market_dataset_id
    ds_dir.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "instrument_id": pa.array(inst_col, pa.int64()),
            "venue_id": pa.array(venue_col, pa.string()),
            "timeframe": pa.array(tf_col, pa.string()),
            "period_start": pa.array(pstart_col, pa.int64()),
            "period_end": pa.array(pend_col, pa.int64()),
            "availability_time": pa.array(avail_col, pa.int64()),
            "open": pa.array(open_col, pa.float64()),
            "high": pa.array(high_col, pa.float64()),
            "low": pa.array(low_col, pa.float64()),
            "close": pa.array(close_col, pa.float64()),
            "base_volume": pa.array(base_vol_col, pa.float64()),
            "quote_volume": pa.array(quote_vol_col, pa.float64()),
            "source_dataset_id": pa.array(src_col, pa.string()),
            "quality_flags": pa.array(flags_col, pa.list_(pa.string())),
        }
    )
    rel_uri = f"market_bars/{market_dataset_id}/part-0.parquet"
    pq.write_table(table, ds_dir / "part-0.parquet")
    conn.execute(
        "INSERT INTO dataset (dataset_id, dataset_type, schema_version, "
        "manifest_sha256, manifest_uri, publication_uri, transform_name, "
        "transform_version, code_commit, config_sha256, row_count, byte_size, "
        "event_start, event_end, availability_start, availability_end, "
        "quality_status, publication_status, created_at) VALUES ("
        "?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            market_dataset_id,
            "market_bars",
            "1",
            "sha256:baseline-bars",
            "m.json",
            "p.json",
            "baseline_synthetic",
            "1",
            "BASE-001",
            "cfg-base",
            n_rows,
            n_rows * 64,
            _iso(start),
            _iso(start + timedelta(days=n_days + 5)),
            _iso(start),
            _iso(start + timedelta(days=n_days + 5)),
            "ACCEPTED",
            "REGISTERED",
            created,
        ),
    )
    conn.execute(
        "INSERT INTO dataset_file (dataset_id, storage_uri, file_sha256, "
        "row_count, byte_size) VALUES (?,?,?,?,?)",
        (market_dataset_id, rel_uri, "sha256:part-base", str(n_rows), str(n_rows * 64)),
    )
    conn.commit()
    conn.close()
    raw = CatalogAsOfStore(control_database=db, dataset_store_root=store_root)
    return raw


@pytest.mark.parametrize(
    "factor_cls",
    [MomentumFactor, MeanReversionFactor, VolumeFactor],
)
def test_baseline_substrate_integration(
    tmp_path: Path,
    factor_cls: type[MomentumFactor | MeanReversionFactor | VolumeFactor],
) -> None:
    """CatalogAsOfStore → factor → Label → Split → ExperimentBundle."""
    n_assets = 8
    n_days = 50
    window = 5
    instruments = list(range(1, n_assets + 1))
    start = datetime(2020, 1, 1, tzinfo=UTC)
    root = tmp_path / factor_cls.factor_id
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    store = _build_catalog_asof(
        root,
        instruments=instruments,
        start=start,
        n_days=n_days,
        price_seed=7,
    )

    label_config = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_DATASET,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=True,
    )
    split_config = SplitConfig(
        mode=SplitMode.WALK_FORWARD,
        train_span=timedelta(days=15),
        test_span=timedelta(days=10),
        embargo=timedelta(days=1),
        min_train_events=n_assets,
        min_test_events=max(2, n_assets // 2),
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
    )
    bundle = ExperimentBundle(
        label_config=label_config,
        split_config=split_config,
        factor_defs=(factor_cls.factor_id,),
        metadata={"name": f"baseline_{factor_cls.factor_id}"},
    )
    reg = InMemoryExperimentRegistry()
    fp = reg.register(bundle)
    assert reg.has(fp)

    factor = factor_cls(store, market_dataset_id=_DATASET, window=window)
    assert isinstance(factor, Factor)
    as_of = start + timedelta(days=31)
    universe = [str(i) for i in instruments]
    frame = factor.compute(universe, as_of)
    assert len(frame.values) == n_assets
    assert all(math.isfinite(v.score) for v in frame.values)

    decision_times = [
        start + timedelta(days=d) for d in range(window + 2, n_days + 1)
    ]
    events = AsOfLabelEngine(store).compute(instruments, decision_times, label_config)
    assert events
    folds = PurgedChronologicalSplitter(store).split(
        [e.to_event_interval() for e in events],
        split_config,
    )
    assert folds
    test_dt = folds[0].test.events[0].decision_time
    frame2 = factor.compute(universe, test_dt)
    assert len(frame2.values) == n_assets


def test_catalog_asof_raw_store_ref_and_completed_bar_access(tmp_path: Path) -> None:
    """Raw CatalogAsOfStore for REF and completed-bar market access.

    With the closed upper-bound window, completed bars are selectable through
    the raw store at ``decision_time = period_end`` (availability_time). REF
    still goes through the raw store with half-open reference windows.
    """
    root = tmp_path / "smoke"
    root.mkdir(parents=True)
    store = _build_catalog_asof(
        root,
        instruments=[1, 2],
        start=datetime(2020, 1, 1, tzinfo=UTC),
        n_days=10,
        price_seed=1,
    )
    t = datetime(2020, 1, 6, tzinfo=UTC)
    assert isinstance(store, CatalogAsOfStore)
    ref = store.as_of(
        _INSTRUMENT_DATASET_ID,
        ["1", "2"],
        ["instrument_id"],
        t,
        knowledge_time=t,
    )
    assert ref.num_rows == 2
    raw_bars = store.latest_available(
        _DATASET, [1], ["instrument_id", "close", "period_start"], t
    )
    assert raw_bars.num_rows == 1
    completed_bars = store.latest_available(
        _DATASET,
        [1],
        ["instrument_id", "close", "period_start", "availability_time"],
        t,
    )
    assert completed_bars.num_rows == 1
