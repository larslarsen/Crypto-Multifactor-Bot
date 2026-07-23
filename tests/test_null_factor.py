"""NULL-001 — null factor has no edge (experiment #18).

Exercises the accepted research substrate end-to-end with the **real**
``CatalogAsOfStore`` (synthetic control DB + market_bars Parquet):

    CatalogAsOfStore (ASOF-001)
      → AsOfLabelEngine (LABEL-001)
      → PurgedChronologicalSplitter (SPLIT-001)
      → ExperimentBundle / InMemoryExperimentRegistry (EXP-001)
      → NullFactor scores for long/short decile simulation

A thin read-through cache wraps CatalogAsOfStore for bar tables only so the
test remains practical (production CatalogAsOfStore reloads Parquet per call;
that I/O is not under test here). Eligibility and bar filtering still execute
the real CatalogAsOfStore code paths on first load / every as_of call.

Factor scores and price paths use independent seeds so expected edge is zero.

Panel size and Sharpe band match ticket NULL-001: 100 assets, 365 days,
mean annualized Sharpe within ±0.5 across 10 trials, win rate 45–55%.
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

from cryptofactors.catalog.as_of import CatalogAsOfStore, observation_eligible
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations
from cryptofactors.factors.contract import Factor, FactorFrame
from cryptofactors.factors.null import NullFactor, NullFactorError
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

_N_ASSETS: int = 100
_N_DAYS: int = 365
_N_TRIALS: int = 10
_HORIZON: timedelta = timedelta(days=1)
_MARKET_DATASET_ID: str = "ds_null_bars"
_INSTRUMENT_DATASET_ID: str = "ref_instrument_version"
_MEAN_SHARPE_TOL: float = 0.5
_TRIAL_SHARPE_TOL: float = 2.5


def _us(dt: datetime) -> int:
    return int(dt.astimezone(UTC).timestamp() * 1_000_000)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sharpe_ratio(returns: list[float], *, periods_per_year: float = 365.0) -> float:
    if len(returns) < 2:
        return 0.0
    mean = statistics.fmean(returns)
    stdev = statistics.stdev(returns)
    if stdev == 0.0:
        return 0.0
    return (mean / stdev) * math.sqrt(periods_per_year)


def _win_rate(returns: list[float]) -> float:
    if not returns:
        return 0.0
    wins = sum(1 for r in returns if r > 0.0)
    return wins / len(returns)


class _CachedCatalogAsOf:
    """CatalogAsOfStore-backed AsOf with indexed market bars (test performance).

    * ``as_of`` always delegates to the real CatalogAsOfStore (REF eligibility,
      SQLite bitemporal windows).
    * ``latest_available`` for market_bars loads Parquet once from the store's
      registered paths, then applies the same ``observation_eligible`` rule the
      store uses, with an in-memory per-instrument index (avoids O(rows) Python
      scans on every label lookup — production I/O pattern is covered by the
      smoke test that calls CatalogAsOfStore.latest_available directly).
    """

    def __init__(self, store: CatalogAsOfStore) -> None:
        self._store = store
        self._bars_by_inst: dict[int, list[tuple[int, int, int | None, float]]] | None = (
            None
        )

    def as_of(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        knowledge_time: datetime | None = None,
    ) -> pa.Table:
        return self._store.as_of(
            dataset_id, keys, fields, decision_time, knowledge_time
        )

    def _ensure_bar_index(self, dataset_id: str) -> None:
        if self._bars_by_inst is not None:
            return
        paths = self._store._dataset_file_paths(dataset_id)
        tables = [pq.read_table(p) for p in paths]
        table = (
            pa.concat_tables(tables, promote_options="default")
            if len(tables) > 1
            else tables[0]
        )
        by_inst: dict[int, list[tuple[int, int, int | None, float]]] = {}
        inst = table.column("instrument_id").to_pylist()
        p_start = table.column("period_start").to_pylist()
        p_end = table.column("period_end").to_pylist()
        avail = table.column("availability_time").to_pylist()
        close = table.column("close").to_pylist()
        for i in range(table.num_rows):
            iid = int(inst[i])
            row = (
                int(avail[i]),
                int(p_start[i]),
                int(p_end[i]) if p_end[i] is not None else None,
                float(close[i]),
            )
            by_inst.setdefault(iid, []).append(row)
        for iid in by_inst:
            by_inst[iid].sort(key=lambda r: (r[1], r[0]))
        self._bars_by_inst = by_inst

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> pa.Table:
        if dataset_id != _MARKET_DATASET_ID:
            return self._store.latest_available(
                dataset_id, keys, fields, decision_time, max_age
            )
        self._ensure_bar_index(dataset_id)
        assert self._bars_by_inst is not None
        t_us = _us(decision_time)
        min_availability_us: int | None = None
        if max_age is not None:
            min_availability_us = t_us - int(max_age.total_seconds() * 1_000_000)

        out_ids: list[int] = []
        out_close: list[float] = []
        out_avail: list[int] = []
        out_pstart: list[int] = []
        for key in keys:
            iid = int(key)
            best: tuple[int, int, int | None, float] | None = None
            for avail_us, vf, vt, close_px in self._bars_by_inst.get(iid, []):
                if min_availability_us is not None and avail_us < min_availability_us:
                    continue
                if not observation_eligible(
                    decision_time_us=t_us,
                    availability_time_us=avail_us,
                    valid_from_us=vf,
                    valid_to_us=vt,
                ):
                    continue
                if best is None or (vf, avail_us) > (best[1], best[0]):
                    best = (avail_us, vf, vt, close_px)
            if best is not None:
                out_ids.append(iid)
                out_close.append(best[3])
                out_avail.append(best[0])
                out_pstart.append(best[1])

        cols: dict[str, pa.Array] = {
            "instrument_id": pa.array(out_ids, pa.int64()),
            "close": pa.array(out_close, pa.float64()),
            "availability_time": pa.array(out_avail, pa.int64()),
            "period_start": pa.array(out_pstart, pa.int64()),
        }
        names = [f for f in fields if f in cols] or list(cols.keys())
        return pa.table({n: cols[n] for n in names})


def _build_catalog_asof(
    root: Path,
    *,
    instruments: list[int],
    start: datetime,
    n_days: int,
    price_seed: int,
) -> _CachedCatalogAsOf:
    """Build real CatalogAsOfStore (+ bar cache) with REF + synthetic market_bars."""
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

    far_end_us = _us(start + timedelta(days=n_days + 60))
    for iid in instruments:
        for day in range(n_days + 5):
            ts = start + timedelta(days=day)
            # Independent levels (not a random walk) so forward returns are pure
            # cross-sectional noise with no serial path dependence.
            close = float(math.exp(rng.gauss(4.6, 0.25)))
            inst_col.append(int(iid))
            venue_col.append("V1")
            tf_col.append("1d")
            pstart_col.append(_us(ts))
            pend_col.append(far_end_us)
            avail_col.append(_us(ts))
            open_col.append(close)
            high_col.append(close * 1.01)
            low_col.append(close * 0.99)
            close_col.append(close)
            base_vol_col.append(1000.0)
            quote_vol_col.append(1000.0 * close)
            src_col.append(_MARKET_DATASET_ID)
            flags_col.append([])
            n_rows += 1

    ds_dir = store_root / "market_bars" / _MARKET_DATASET_ID
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
    rel_uri = f"market_bars/{_MARKET_DATASET_ID}/part-0.parquet"
    pq.write_table(table, ds_dir / "part-0.parquet")

    conn.execute(
        "INSERT INTO dataset (dataset_id, dataset_type, schema_version, "
        "manifest_sha256, manifest_uri, publication_uri, transform_name, "
        "transform_version, code_commit, config_sha256, row_count, byte_size, "
        "event_start, event_end, availability_start, availability_end, "
        "quality_status, publication_status, created_at) VALUES ("
        "?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            _MARKET_DATASET_ID,
            "market_bars",
            "1",
            "sha256:null-bars",
            "m.json",
            "p.json",
            "null_synthetic",
            "1",
            "NULL-001",
            "cfg-null",
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
        (_MARKET_DATASET_ID, rel_uri, "sha256:part-null", str(n_rows), str(n_rows * 64)),
    )
    conn.commit()
    conn.close()
    raw = CatalogAsOfStore(control_database=db, dataset_store_root=store_root)
    return _CachedCatalogAsOf(raw)


def _run_null_substrate_trial(
    root: Path,
    *,
    trial_seed: int,
    n_assets: int = _N_ASSETS,
    n_days: int = _N_DAYS,
    decile: int = 10,
) -> tuple[float, float]:
    """NullFactor through CatalogAsOfStore → LABEL → SPLIT → EXP → long/short."""
    instruments = list(range(1, n_assets + 1))
    start = datetime(2020, 1, 1, tzinfo=UTC)
    decision_times = [start + timedelta(days=d) for d in range(1, n_days + 1)]

    trial_root = root / f"trial_{trial_seed}"
    if trial_root.exists():
        shutil.rmtree(trial_root)
    trial_root.mkdir(parents=True, exist_ok=True)
    as_of_store = _build_catalog_asof(
        trial_root,
        instruments=instruments,
        start=start,
        n_days=n_days,
        price_seed=trial_seed + 17_001,
    )

    label_config = LabelConfig(
        horizon=_HORIZON,
        label_type=LabelType.FORWARD_RETURN,
        min_gap=timedelta(0),
        market_dataset_id=_MARKET_DATASET_ID,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
        require_instrument_eligibility=True,
    )
    split_config = SplitConfig(
        mode=SplitMode.WALK_FORWARD,
        train_span=timedelta(days=60),
        test_span=timedelta(days=30),
        embargo=timedelta(days=1),
        min_train_events=max(10, n_assets),
        min_test_events=max(5, n_assets // 2),
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
    )

    bundle = ExperimentBundle(
        label_config=label_config,
        split_config=split_config,
        factor_defs=(NullFactor.factor_id,),
        metadata={
            "name": "null_factor_experiment_18",
            "trial_seed": trial_seed,
            "n_assets": n_assets,
            "n_days": n_days,
        },
    )
    registry = InMemoryExperimentRegistry()
    fingerprint = registry.register(bundle)
    assert registry.has(fingerprint)
    assert registry.load(fingerprint).fingerprint == fingerprint

    factor = NullFactor(seed=trial_seed)
    assert isinstance(factor, Factor)

    label_engine = AsOfLabelEngine(as_of_store)
    events = label_engine.compute(instruments, decision_times, label_config)
    assert events

    splitter = PurgedChronologicalSplitter(as_of_store)
    folds = splitter.split(
        [e.to_event_interval() for e in events],
        split_config,
    )
    assert folds

    label_by_key = {(str(e.instrument_id), e.decision_time): e for e in events}
    score_cache: dict[datetime, dict[str, float]] = {}
    universe = [str(i) for i in instruments]
    k = max(1, n_assets // decile)
    daily_by_decision: dict[datetime, float] = {}

    for fold in folds:
        by_decision: dict[datetime, list[str]] = {}
        for ev in fold.test.events:
            by_decision.setdefault(ev.decision_time, []).append(str(ev.instrument_id))
        for decision_time in sorted(by_decision.keys()):
            if decision_time in daily_by_decision:
                continue
            if decision_time not in score_cache:
                frame = factor.compute(universe, decision_time)
                assert isinstance(frame, FactorFrame)
                score_cache[decision_time] = {
                    v.instrument_id: v.score for v in frame.values
                }
            scores = score_cache[decision_time]
            insts = by_decision[decision_time]
            ranked = sorted(insts, key=lambda i: scores[i], reverse=True)
            if len(ranked) < 2 * k:
                continue
            longs = ranked[:k]
            shorts = ranked[-k:]
            long_rets: list[float] = []
            short_rets: list[float] = []
            for iid in longs:
                lab = label_by_key.get((iid, decision_time))
                if lab is None:
                    continue
                long_rets.append(float(lab.label_value))
            for iid in shorts:
                lab = label_by_key.get((iid, decision_time))
                if lab is None:
                    continue
                short_rets.append(float(lab.label_value))
            if not long_rets or not short_rets:
                continue
            daily_by_decision[decision_time] = (
                statistics.fmean(long_rets) - statistics.fmean(short_rets)
            )

    daily = [daily_by_decision[t] for t in sorted(daily_by_decision.keys())]
    assert daily, "substrate trial produced no portfolio returns"
    assert len(daily) >= 40, f"too few portfolio days for Sharpe SE control: {len(daily)}"
    return _sharpe_ratio(daily), _win_rate(daily)


@pytest.fixture(scope="module")
def null_trials_seed0(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[list[float], list[float]]:
    root = tmp_path_factory.mktemp("null_seed0")
    sharpes: list[float] = []
    wins: list[float] = []
    for trial in range(_N_TRIALS):
        s, w = _run_null_substrate_trial(root, trial_seed=trial)
        sharpes.append(s)
        wins.append(w)
    return sharpes, wins


@pytest.fixture(scope="module")
def null_trials_seed100(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[list[float], list[float]]:
    root = tmp_path_factory.mktemp("null_seed100")
    sharpes: list[float] = []
    wins: list[float] = []
    for trial in range(_N_TRIALS):
        s, w = _run_null_substrate_trial(root, trial_seed=100 + trial)
        sharpes.append(s)
        wins.append(w)
    return sharpes, wins


def test_null_factor_is_factor_protocol() -> None:
    factor = NullFactor(seed=1)
    assert isinstance(factor, Factor)
    assert factor.factor_id == "null"
    assert factor.factor_version == "1"


def test_null_factor_compute_deterministic() -> None:
    factor = NullFactor(seed=42)
    universe = ("eth", "btc", "sol")
    as_of = datetime(2021, 6, 1, tzinfo=UTC)
    a = factor.compute(universe, as_of)
    b = factor.compute(universe, as_of)
    assert [v.score for v in a.values] == [v.score for v in b.values]
    assert [v.instrument_id for v in a.values] == ["btc", "eth", "sol"]


def test_null_factor_scores_universe_stable() -> None:
    factor = NullFactor(seed=7)
    as_of = datetime(2022, 1, 1, tzinfo=UTC)
    small = factor.compute(("btc", "eth"), as_of)
    large = factor.compute(("sol", "btc", "eth", "ada"), as_of)
    small_map = {v.instrument_id: v.score for v in small.values}
    large_map = {v.instrument_id: v.score for v in large.values}
    assert small_map["btc"] == large_map["btc"]
    assert small_map["eth"] == large_map["eth"]


def test_null_factor_scores_differ_by_instrument() -> None:
    factor = NullFactor(seed=7)
    as_of = datetime(2022, 1, 1, tzinfo=UTC)
    frame = factor.compute(("a", "b", "c", "d"), as_of)
    scores = [v.score for v in frame.values]
    assert len(set(scores)) == len(scores)


def test_null_factor_rejects_string_universe() -> None:
    factor = NullFactor(seed=0)
    as_of = datetime(2020, 1, 1, tzinfo=UTC)
    with pytest.raises(NullFactorError, match="not str/bytes"):
        factor.compute("btc", as_of)
    with pytest.raises(NullFactorError, match="not str/bytes"):
        factor.compute(b"btc", as_of)  # type: ignore[arg-type]


def test_null_factor_rejects_naive_inputs() -> None:
    factor = NullFactor(seed=0)
    as_of = datetime(2020, 1, 1, tzinfo=UTC)
    with pytest.raises(NullFactorError):
        factor.compute((), as_of)
    with pytest.raises(NullFactorError):
        factor.compute(("btc",), datetime(2020, 1, 1))
    with pytest.raises(NullFactorError):
        factor.compute((123,), as_of)  # type: ignore[arg-type]


def test_null_factor_sharpe_near_zero_ten_trials(
    null_trials_seed0: tuple[list[float], list[float]],
) -> None:
    sharpes, _wins = null_trials_seed0
    mean_sharpe = statistics.fmean(sharpes)
    assert abs(mean_sharpe) <= _MEAN_SHARPE_TOL, (
        f"mean sharpe={mean_sharpe}, trials={sharpes}"
    )
    assert all(abs(s) <= _TRIAL_SHARPE_TOL for s in sharpes), f"trial sharpes={sharpes}"


def test_null_factor_win_rate_near_half_ten_trials(
    null_trials_seed0: tuple[list[float], list[float]],
) -> None:
    _sharpes, wins = null_trials_seed0
    mean_win = statistics.fmean(wins)
    assert 0.45 <= mean_win <= 0.55, f"mean win_rate={mean_win}, trials={wins}"
    assert all(0.40 <= w <= 0.60 for w in wins), f"trial win_rates={wins}"


def test_null_factor_ten_trials_consistent(
    null_trials_seed100: tuple[list[float], list[float]],
) -> None:
    sharpes, wins = null_trials_seed100
    mean_sharpe = statistics.fmean(sharpes)
    mean_win = statistics.fmean(wins)
    assert abs(mean_sharpe) <= _MEAN_SHARPE_TOL, f"mean sharpe={mean_sharpe}"
    assert 0.45 <= mean_win <= 0.55, f"mean win_rate={mean_win}"
    assert statistics.pstdev(sharpes) < 1.5
    assert statistics.pstdev(wins) < 0.05


def test_experiment_bundle_registers_null_factor() -> None:
    label_config = LabelConfig(
        horizon=_HORIZON,
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id=_MARKET_DATASET_ID,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
    )
    split_config = SplitConfig(
        mode=SplitMode.PURGED_KFOLD,
        n_folds=3,
        instrument_dataset_id=_INSTRUMENT_DATASET_ID,
    )
    bundle = ExperimentBundle(
        label_config=label_config,
        split_config=split_config,
        factor_defs=(NullFactor.factor_id,),
        metadata={"name": "null_only"},
    )
    reg = InMemoryExperimentRegistry()
    fp = reg.register(bundle)
    assert len(fp) == 64
    assert reg.list_bundles() == [fp]


def test_catalog_asof_latest_available_smoke(tmp_path: Path) -> None:
    """Direct CatalogAsOfStore path: synthetic bars readable via real store."""
    instruments = [1, 2, 3]
    start = datetime(2020, 1, 1, tzinfo=UTC)
    smoke_root = tmp_path / "smoke"
    smoke_root.mkdir(parents=True, exist_ok=True)
    cached = _build_catalog_asof(
        smoke_root,
        instruments=instruments,
        start=start,
        n_days=10,
        price_seed=1,
    )
    t = start + timedelta(days=5)
    table = cached.latest_available(
        _MARKET_DATASET_ID,
        instruments,
        ["instrument_id", "close", "availability_time"],
        t,
    )
    assert table.num_rows == 3
    ref = cached.as_of(
        _INSTRUMENT_DATASET_ID,
        [str(i) for i in instruments],
        ["instrument_id"],
        t,
        knowledge_time=t,
    )
    assert ref.num_rows == 3
    raw = cached._store.latest_available(
        _MARKET_DATASET_ID,
        [1],
        ["instrument_id", "close"],
        t,
    )
    assert raw.num_rows == 1
