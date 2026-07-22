"""SPLIT-001 — focused integration tests for the approved purged split engine.

Covers:
- all three modes (walk_forward / expanding / purged_kfold)
- purge + embargo rules (no train/test event-time overlap; embargo gap)
- AsOf injection + instrument eligibility (structural AsOfDataAccess protocol; also the
  real CatalogAsOfStore injected)
- error paths (insufficient history, bad config, missing instruments)

The approved drop (``cryptofactors.validation.split``) is not modified here. Tests inject a
minimal in-memory ``AsOfDataAccess`` so no catalog/DB is required; one test additionally
injects the real ``CatalogAsOfStore`` to prove the contract surface matches end-to-end.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
import pytest

from cryptofactors.validation.split import (
    EventInterval,
    OuterFold,
    PurgedChronologicalSplitter,
    SplitConfig,
    SplitError,
    SplitMode,
    purge_train_events,
)


UTC = timezone.utc


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s + "Z" if not s.endswith("Z") else s).astimezone(UTC)


def _utc(dt: datetime) -> datetime:
    return dt.astimezone(UTC)


# ---------------------------------------------------------------------------
# In-memory AsOfDataAccess fake (structural protocol; no catalog)
# ---------------------------------------------------------------------------

class _FakeAsOf:
    """Returns exactly the instruments declared eligible at each decision time."""

    def __init__(self, eligible: dict[datetime, set[str]]) -> None:
        self._eligible = {_utc(k): v for k, v in eligible.items()}
        self.calls: list[object] = []

    def as_of(
        self,
        dataset_id: str,
        keys: Sequence[str | int],
        fields: Sequence[str],
        decision_time: datetime,
        knowledge_time: datetime | None = None,
    ) -> pa.Table:
        self.calls.append((dataset_id, tuple(keys), tuple(fields), decision_time, knowledge_time))
        d = _utc(decision_time)
        present = self._eligible.get(d, set())
        return pa.table({"instrument_id": pa.array(list(present), pa.string())})

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[str | int],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> pa.Table:
        return self.as_of(dataset_id, keys, fields, decision_time, knowledge_time=decision_time)


def _ev(instrument_id: str, decision_time: str, start: str, end: str, event_id: str | None = None) -> EventInterval:
    return EventInterval(
        instrument_id=instrument_id,
        decision_time=_ts(decision_time),
        event_start=_ts(start),
        event_end=_ts(end),
        event_id=event_id,
    )


def _make_events(instruments: tuple[str, str] = ("AAA", "BBB"), n_per: int = 6) -> list[EventInterval]:
    """Evenly spaced daily decision events across two instruments."""
    base = _ts("2021-01-01T00:00:00Z")
    events: list[EventInterval] = []
    for i in range(n_per):
        d = base + timedelta(days=i)
        for inst in instruments:
            events.append(
                _ev(
                    inst,
                    d.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    d.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    (d + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    f"{inst}-{i}",
                )
            )
    return events


def _all_eligible(events: list[EventInterval]) -> dict[datetime, set[str]]:
    out: dict[datetime, set[str]] = {}
    for e in events:
        out.setdefault(_utc(e.decision_time), set()).add(str(e.instrument_id))
    return out


# ---------------------------------------------------------------------------
# EventInterval validation
# ---------------------------------------------------------------------------

def test_event_interval_rejects_non_utc() -> None:
    with pytest.raises(SplitError):
        EventInterval("AAA", datetime(2021, 1, 1), _ts("2021-01-01T00:00:00Z"), _ts("2021-01-02T00:00:00Z"))


def test_event_interval_rejects_event_end_le_start() -> None:
    with pytest.raises(SplitError):
        _ev("AAA", "2021-01-01T00:00:00Z", "2021-01-02T00:00:00Z", "2021-01-02T00:00:00Z")


def test_event_interval_rejects_decision_after_event_end() -> None:
    with pytest.raises(SplitError):
        _ev("AAA", "2021-01-03T00:00:00Z", "2021-01-01T00:00:00Z", "2021-01-02T00:00:00Z")


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

def test_config_purged_kfold_requires_n_folds() -> None:
    with pytest.raises(SplitError):
        SplitConfig(mode=SplitMode.PURGED_KFOLD, n_folds=1)


def test_config_walk_forward_requires_spans() -> None:
    with pytest.raises(SplitError):
        SplitConfig(mode=SplitMode.WALK_FORWARD, n_folds=3)


def test_config_rejects_negative_embargo() -> None:
    with pytest.raises(SplitError):
        SplitConfig(mode=SplitMode.EXPANDING, train_span=timedelta(days=10), test_span=timedelta(days=2), embargo=timedelta(days=-1))


def test_config_rejects_min_events_zero() -> None:
    with pytest.raises(SplitError):
        SplitConfig(mode=SplitMode.EXPANDING, train_span=timedelta(days=10), test_span=timedelta(days=2), min_train_events=0)


# ---------------------------------------------------------------------------
# purge_train_events unit behavior
# ---------------------------------------------------------------------------

def test_purge_removes_overlapping_train_events() -> None:
    train = [
        _ev("AAA", "2021-01-01T00:00:00Z", "2021-01-01T00:00:00Z", "2021-01-02T00:00:00Z"),
        _ev("AAA", "2021-03-01T00:00:00Z", "2021-03-01T00:00:00Z", "2021-03-02T00:00:00Z"),
    ]
    test = [_ev("AAA", "2021-02-01T00:00:00Z", "2021-02-01T00:00:00Z", "2021-02-05T00:00:00Z")]
    kept = purge_train_events(train, test, embargo=timedelta(0))
    # Mar train event_end (03-01) is strictly after the Feb test purge horizon, so it is
    # purged. Jan train (event_end 01-02, before horizon, no overlap) is kept.
    assert len(kept) == 1
    assert kept[0].instrument_id == "AAA"
    assert kept[0].decision_time == _ts("2021-01-01T00:00:00Z")


def test_purge_removes_train_before_test_decision_horizon() -> None:
    train = [_ev("AAA", "2021-01-31T00:00:00Z", "2021-01-31T00:00:00Z", "2021-02-01T00:00:00Z")]
    test = [_ev("AAA", "2021-02-01T00:00:00Z", "2021-02-01T00:00:00Z", "2021-02-05T00:00:00Z")]
    kept = purge_train_events(train, test, embargo=timedelta(0))
    # train decision (01-31) precedes the test horizon (02-01) and event_end (02-01) is not
    # strictly after it, so this train event is retained (purge only removes leakage).
    assert len(kept) == 1


def test_purge_respects_embargo_gap() -> None:
    train = [_ev("AAA", "2021-02-01T00:00:00Z", "2021-02-01T00:00:00Z", "2021-02-02T00:00:00Z")]
    test = [_ev("AAA", "2021-02-10T00:00:00Z", "2021-02-10T00:00:00Z", "2021-02-15T00:00:00Z")]
    kept = purge_train_events(train, test, embargo=timedelta(days=5))
    # purge_horizon = test decision - embargo = 2021-02-05; train event_end 2021-02-02 < horizon → kept
    assert len(kept) == 1


# ---------------------------------------------------------------------------
# All three modes produce folds
# ---------------------------------------------------------------------------

def test_walk_forward_produces_folds() -> None:
    events = _make_events()
    store = _FakeAsOf(_all_eligible(events))
    cfg = SplitConfig(
        mode=SplitMode.WALK_FORWARD,
        train_span=timedelta(days=3),
        test_span=timedelta(days=1),
        embargo=timedelta(days=0),
    )
    folds = PurgedChronologicalSplitter(store).split(events, cfg)
    assert len(folds) >= 1
    for f in folds:
        assert isinstance(f, OuterFold)
        assert f.train.end <= f.test.start  # embargo gap respected (>= here, 0 embargo)
        assert len(f.test.events) >= cfg.min_test_events


def test_expanding_produces_folds() -> None:
    events = _make_events()
    store = _FakeAsOf(_all_eligible(events))
    cfg = SplitConfig(
        mode=SplitMode.EXPANDING,
        train_span=timedelta(days=3),
        test_span=timedelta(days=1),
        embargo=timedelta(days=0),
    )
    folds = PurgedChronologicalSplitter(store).split(events, cfg)
    assert len(folds) >= 1
    # Expanding: later folds' train windows start at t0 (no earlier bound shift).
    first = folds[0]
    # train start is the global t0 for expanding
    assert first.train.start == min(e.decision_time for e in events)


def test_purged_kfold_produces_folds() -> None:
    events = _make_events(n_per=12)
    store = _FakeAsOf(_all_eligible(events))
    cfg = SplitConfig(mode=SplitMode.PURGED_KFOLD, n_folds=3)
    folds = PurgedChronologicalSplitter(store).split(events, cfg)
    # 3 blocks of 8; the first block has no prior train history so it is skipped fail-closed,
    # yielding exactly 2 valid folds.
    assert len(folds) == 2
    for f in folds:
        assert f.purge_gap_start <= f.purge_gap_end


# ---------------------------------------------------------------------------
# Purge + embargo enforced inside produced folds
# ---------------------------------------------------------------------------

def test_folds_have_no_train_test_event_overlap() -> None:
    events = _make_events()
    store = _FakeAsOf(_all_eligible(events))
    cfg = SplitConfig(
        mode=SplitMode.EXPANDING,
        train_span=timedelta(days=3),
        test_span=timedelta(days=1),
        embargo=timedelta(days=1),
    )
    folds = PurgedChronologicalSplitter(store).split(events, cfg)
    for f in folds:
        test_ids = {e.event_id for e in f.test.events}
        for tr in f.train.events:
            # same event must not appear in both; overlap rule via event_id uniqueness here
            assert tr.event_id not in test_ids
        # embargo gap present
        assert (f.test.start - f.train.end) >= cfg.embargo


def test_purged_kfold_test_blocks_disjoint_by_event() -> None:
    events = _make_events(n_per=9)
    store = _FakeAsOf(_all_eligible(events))
    cfg = SplitConfig(mode=SplitMode.PURGED_KFOLD, n_folds=3)
    folds = PurgedChronologicalSplitter(store).split(events, cfg)
    seen_test_ids: set[str] = set()
    for f in folds:
        for te in f.test.events:
            assert te.event_id not in seen_test_ids
            seen_test_ids.add(te.event_id or "")


# ---------------------------------------------------------------------------
# AsOf injection + instrument eligibility
# ---------------------------------------------------------------------------

def test_splitter_rejects_none_store() -> None:
    with pytest.raises(SplitError):
        PurgedChronologicalSplitter(None)  # type: ignore[arg-type]


def test_instrument_eligibility_missing_instrument_raises() -> None:
    events = _make_events()
    # Make BBB ineligible at every decision time.
    eligible = _all_eligible(events)
    for k in eligible:
        eligible[k] = {x for x in eligible[k] if x != "BBB"}
    store = _FakeAsOf(eligible)
    cfg = SplitConfig(
        mode=SplitMode.EXPANDING,
        train_span=timedelta(days=3),
        test_span=timedelta(days=1),
    )
    with pytest.raises(SplitError, match="instrument not eligible"):
        PurgedChronologicalSplitter(store).split(events, cfg)


def test_real_catalog_asof_injected_end_to_end(tmp_path: Path) -> None:
    """Inject the real CatalogAsOfStore to prove the AsOfDataAccess surface matches."""
    from cryptofactors.catalog.as_of import CatalogAsOfStore
    from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations
    import sqlite3

    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("INSERT INTO ref_venue VALUES ('V1','V1','Venue','CEX','2020-01-01T00:00:00Z')")
    conn.execute("INSERT INTO ref_asset VALUES ('A1','CRYPTO','Asset','2020-01-01T00:00:00Z')")
    conn.execute(
        "INSERT INTO ref_instrument VALUES ('INST1','A1','V1','PERPETUAL','A1','A1','2020-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO ref_instrument_version VALUES ("
        "'IV1','INST1',1,'{}','2020-01-01T00:00:00Z','2030-01-01T00:00:00Z',"
        "'2020-01-01T00:00:00Z','2030-01-01T00:00:00Z',NULL,'{}')"
    )
    conn.commit()
    conn.close()

    events = [
        _ev("INST1", "2021-01-01T00:00:00Z", "2021-01-01T00:00:00Z", "2021-01-02T00:00:00Z", "e1"),
        _ev("INST1", "2021-01-05T00:00:00Z", "2021-01-05T00:00:00Z", "2021-01-06T00:00:00Z", "e2"),
        _ev("INST1", "2021-01-09T00:00:00Z", "2021-01-09T00:00:00Z", "2021-01-10T00:00:00Z", "e3"),
    ]
    store = CatalogAsOfStore(control_database=db, dataset_store_root=None)
    cfg = SplitConfig(
        mode=SplitMode.EXPANDING,
        train_span=timedelta(days=2),
        test_span=timedelta(days=1),
        instrument_dataset_id="ref_instrument_version",
    )
    folds = PurgedChronologicalSplitter(store).split(events, cfg)
    assert len(folds) >= 1


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

def test_empty_events_raises() -> None:
    store = _FakeAsOf({})
    with pytest.raises(SplitError, match="non-empty"):
        PurgedChronologicalSplitter(store).split([], SplitConfig(mode=SplitMode.EXPANDING, train_span=timedelta(days=1), test_span=timedelta(days=1)))


def test_insufficient_history_raises() -> None:
    events = _make_events(n_per=2)  # too few for multi-fold windows
    store = _FakeAsOf(_all_eligible(events))
    cfg = SplitConfig(
        mode=SplitMode.WALK_FORWARD,
        train_span=timedelta(days=30),
        test_span=timedelta(days=1),
    )
    # Either folds form with tiny content or it fails closed; here history < train_span → no fold.
    with pytest.raises(SplitError, match="insufficient history"):
        PurgedChronologicalSplitter(store).split(events, cfg)


def test_purged_kfold_insufficient_distinct_times_raises() -> None:
    # All events share one decision_time → < n_folds distinct times.
    d = "2021-01-01T00:00:00Z"
    events = [
        _ev("AAA", d, d, "2021-01-02T00:00:00Z", "a1"),
        _ev("BBB", d, d, "2021-01-02T00:00:00Z", "b1"),
    ]
    store = _FakeAsOf(_all_eligible(events))
    cfg = SplitConfig(mode=SplitMode.PURGED_KFOLD, n_folds=3)
    with pytest.raises(SplitError, match="distinct decision_times"):
        PurgedChronologicalSplitter(store).split(events, cfg)
