"""LABEL-001 — focused integration tests for the approved label / event-interval engine.

Covers (per Jr contract):
- DecisionEvent separation (event_start >= decision_time + min_gap; fail on end<=start;
  fail on event_start < decision_time)
- all three label types: forward_return, sign, binary
- price fetch via AsOf (entry at decision_time, exit at event_end)
- instrument eligibility via AsOf; missing -> fail closed
- deterministic ordering; empty inputs -> error
- insufficient price data -> LabelError
- to_event_interval() bridge to SPLIT-001

The approved drop (``cryptofactors.validation.labels``) is not modified here. Tests inject a
minimal in-memory ``AsOfDataAccess`` (structural protocol; no catalog import).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pyarrow as pa
import pytest

from cryptofactors.validation.labels import (
    AsOfLabelEngine,
    DecisionEvent,
    LabelConfig,
    LabelError,
    LabelType,
)
from cryptofactors.validation.split import PurgedChronologicalSplitter, SplitConfig, SplitMode


UTC = timezone.utc


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s + "Z" if not s.endswith("Z") else s).astimezone(UTC)


class _FakeAsOf:
    """Minimal AsOfDataAccess: per-instrument price timeline + eligibility set."""

    def __init__(
        self,
        eligible: dict[datetime, set[str]],
        prices: dict[str, list[tuple[datetime, str]]],
    ) -> None:
        # prices: instrument_id -> list of (availability_time, close_str)
        self._eligible = {d.astimezone(UTC): v for d, v in eligible.items()}
        self._prices = {
            k: [(t.astimezone(UTC), p) for t, p in v] for k, v in prices.items()
        }
        self.as_of_calls: list[object] = []
        self.latest_call_times: list[datetime] = []

    def as_of(
        self,
        dataset_id: str,
        keys: Sequence[str | int],
        fields: Sequence[str],
        decision_time: datetime,
        knowledge_time: datetime | None = None,
    ) -> pa.Table:
        self.as_of_calls.append((dataset_id, tuple(keys), tuple(fields), decision_time))
        d = decision_time.astimezone(UTC)
        found = self._eligible.get(d, set())
        return pa.table({"instrument_id": pa.array(list(found), pa.string())})

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[str | int],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> pa.Table:
        self.latest_call_times.append(decision_time)
        inst = str(keys[0])
        d = decision_time.astimezone(UTC)
        timeline = self._prices.get(inst, [])
        # latest availability_time <= d
        chosen = None
        for avail, close in timeline:
            if avail <= d:
                chosen = (avail, close)
            else:
                break
        if chosen is None:
            return pa.table(
                {
                    "instrument_id": pa.array([], pa.string()),
                    "close": pa.array([], pa.string()),
                    "availability_time": pa.array([], pa.int64()),
                    "period_start": pa.array([], pa.int64()),
                }
            )
        avail, close = chosen
        return pa.table(
            {
                "instrument_id": pa.array([inst], pa.string()),
                "close": pa.array([close], pa.string()),
                "availability_time": pa.array([int(avail.timestamp() * 1_000_000)], pa.int64()),
                "period_start": pa.array([int(avail.timestamp() * 1_000_000)], pa.int64()),
            }
        )


def _eligibility(events: list[tuple[datetime, str]]) -> dict[datetime, set[str]]:
    out: dict[datetime, set[str]] = {}
    for dt, inst in events:
        out.setdefault(dt.astimezone(UTC), set()).add(inst)
    return out


def _price_timeline(inst: str, pairs: list[tuple[str, str]]) -> dict[str, list[tuple[datetime, str]]]:
    return {inst: [(_ts(t), p) for t, p in pairs]}


# ---------------------------------------------------------------------------
# DecisionEvent separation contract
# ---------------------------------------------------------------------------

def test_decision_event_rejects_end_le_start() -> None:
    with pytest.raises(LabelError):
        DecisionEvent(
            instrument_id="AAA",
            decision_time=_ts("2021-01-01T00:00:00Z"),
            event_start=_ts("2021-01-02T00:00:00Z"),
            event_end=_ts("2021-01-02T00:00:00Z"),
            label_type=LabelType.FORWARD_RETURN,
            label_value=Decimal("0"),
            label_direction=0,
            entry_price=Decimal("100"),
            exit_price=Decimal("100"),
        )


def test_decision_event_rejects_event_start_before_decision() -> None:
    with pytest.raises(LabelError):
        DecisionEvent(
            instrument_id="AAA",
            decision_time=_ts("2021-01-02T00:00:00Z"),
            event_start=_ts("2021-01-01T00:00:00Z"),
            event_end=_ts("2021-01-03T00:00:00Z"),
            label_type=LabelType.FORWARD_RETURN,
            label_value=Decimal("0"),
            label_direction=0,
            entry_price=Decimal("100"),
            exit_price=Decimal("100"),
        )


def test_decision_event_accepts_min_gap_separation() -> None:
    e = DecisionEvent(
        instrument_id="AAA",
        decision_time=_ts("2021-01-01T00:00:00Z"),
        event_start=_ts("2021-01-01T01:00:00Z"),  # >= decision + min_gap(1h)
        event_end=_ts("2021-01-02T00:00:00Z"),
        label_type=LabelType.FORWARD_RETURN,
        label_value=Decimal("0"),
        label_direction=0,
        entry_price=Decimal("100"),
        exit_price=Decimal("100"),
    )
    assert e.event_start >= e.decision_time


def test_label_config_rejects_nonpositive_horizon() -> None:
    with pytest.raises(LabelError):
        LabelConfig(horizon=timedelta(0), label_type=LabelType.SIGN, market_dataset_id="bars")


def test_label_config_rejects_empty_market_dataset() -> None:
    with pytest.raises(LabelError):
        LabelConfig(horizon=timedelta(days=1), label_type=LabelType.SIGN, market_dataset_id="")


# ---------------------------------------------------------------------------
# All three label types
# ---------------------------------------------------------------------------

def _store_up_down() -> _FakeAsOf:
    elig = _eligibility([
        (_ts("2021-01-01T00:00:00Z"), "AAA"),
        (_ts("2021-01-01T00:00:00Z"), "BBB"),
        (_ts("2021-01-02T00:00:00Z"), "AAA"),
        (_ts("2021-01-02T00:00:00Z"), "BBB"),
    ])
    prices: dict[str, list[tuple[datetime, str]]] = {}
    prices.update(_price_timeline("AAA", [("2021-01-01T00:00:00Z", "100"), ("2021-01-02T00:00:00Z", "110")]))
    prices.update(_price_timeline("BBB", [("2021-01-01T00:00:00Z", "100"), ("2021-01-02T00:00:00Z", "90")]))
    return _FakeAsOf(elig, prices)


def test_forward_return_label() -> None:
    store = _store_up_down()
    cfg = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.FORWARD_RETURN,
        market_dataset_id="bars",
        instrument_dataset_id="ref_instrument_version",
    )
    events = AsOfLabelEngine(store).compute(
        ["AAA", "BBB"],
        [_ts("2021-01-01T00:00:00Z")],
        cfg,
    )
    by_inst = {e.instrument_id: e for e in events}
    # AAA: 100 -> 110 => +0.10 ; BBB: 100 -> 90 => -0.10
    assert by_inst["AAA"].label_value == Decimal("0.1")
    assert by_inst["AAA"].label_direction == 1
    assert by_inst["BBB"].label_value == Decimal("-0.1")
    assert by_inst["BBB"].label_direction == -1


def test_sign_label() -> None:
    store = _store_up_down()
    cfg = LabelConfig(horizon=timedelta(days=1), label_type=LabelType.SIGN, market_dataset_id="bars")
    events = AsOfLabelEngine(store).compute(["AAA", "BBB"], [_ts("2021-01-01T00:00:00Z")], cfg)
    by_inst = {e.instrument_id: e for e in events}
    assert by_inst["AAA"].label_value == Decimal("1")
    assert by_inst["BBB"].label_value == Decimal("-1")


def test_binary_label_threshold() -> None:
    store = _store_up_down()
    cfg = LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.BINARY,
        binary_threshold=Decimal("0"),
        market_dataset_id="bars",
    )
    events = AsOfLabelEngine(store).compute(["AAA", "BBB"], [_ts("2021-01-01T00:00:00Z")], cfg)
    by_inst = {e.instrument_id: e for e in events}
    assert by_inst["AAA"].label_value == Decimal("1")  # +0.1 > 0
    assert by_inst["BBB"].label_value == Decimal("0")  # -0.1 <= 0


# ---------------------------------------------------------------------------
# Price fetch via AsOf (entry at decision, exit at event_end)
# ---------------------------------------------------------------------------

def test_entry_exit_prices_from_asof() -> None:
    store = _store_up_down()
    cfg = LabelConfig(horizon=timedelta(days=1), label_type=LabelType.FORWARD_RETURN, market_dataset_id="bars")
    events = AsOfLabelEngine(store).compute(["AAA"], [_ts("2021-01-01T00:00:00Z")], cfg)
    e = events[0]
    assert e.entry_price == Decimal("100")
    assert e.exit_price == Decimal("110")
    # entry looked up at decision_time; exit at event_end (2021-01-02)
    assert _ts("2021-01-01T00:00:00Z") in store.latest_call_times
    assert _ts("2021-01-02T00:00:00Z") in store.latest_call_times


# ---------------------------------------------------------------------------
# Instrument eligibility via AsOf; missing -> fail closed
# ---------------------------------------------------------------------------

def test_engine_rejects_none_store() -> None:
    with pytest.raises(LabelError):
        AsOfLabelEngine(None)  # type: ignore[arg-type]


def test_missing_instrument_fails_closed() -> None:
    elig = _eligibility([(_ts("2021-01-01T00:00:00Z"), "AAA")])  # BBB absent
    prices: dict[str, list[tuple[datetime, str]]] = {}
    prices.update(_price_timeline("AAA", [("2021-01-01T00:00:00Z", "100"), ("2021-01-02T00:00:00Z", "110")]))
    prices.update(_price_timeline("BBB", [("2021-01-01T00:00:00Z", "100"), ("2021-01-02T00:00:00Z", "90")]))
    store = _FakeAsOf(elig, prices)
    cfg = LabelConfig(horizon=timedelta(days=1), label_type=LabelType.FORWARD_RETURN, market_dataset_id="bars")
    with pytest.raises(LabelError, match="instrument not eligible"):
        AsOfLabelEngine(store).compute(["AAA", "BBB"], [_ts("2021-01-01T00:00:00Z")], cfg)


# ---------------------------------------------------------------------------
# Deterministic ordering
# ---------------------------------------------------------------------------

def test_compute_is_deterministic() -> None:
    store = _store_up_down()
    cfg = LabelConfig(horizon=timedelta(days=1), label_type=LabelType.FORWARD_RETURN, market_dataset_id="bars")
    insts = ["BBB", "AAA"]
    times = [_ts("2021-01-02T00:00:00Z"), _ts("2021-01-01T00:00:00Z")]
    a = AsOfLabelEngine(store).compute(insts, times, cfg)
    b = AsOfLabelEngine(store).compute(insts, times, cfg)
    assert [e.event_id for e in a] == [e.event_id for e in b]
    # order is by (decision_time, instrument_id)
    assert a[0].decision_time <= a[-1].decision_time
    assert a[0].instrument_id == "AAA"


# ---------------------------------------------------------------------------
# Empty inputs -> error
# ---------------------------------------------------------------------------

def test_empty_instruments_raises() -> None:
    store = _store_up_down()
    cfg = LabelConfig(horizon=timedelta(days=1), label_type=LabelType.FORWARD_RETURN, market_dataset_id="bars")
    with pytest.raises(LabelError, match="instruments must be non-empty"):
        AsOfLabelEngine(store).compute([], [_ts("2021-01-01T00:00:00Z")], cfg)


def test_empty_decision_times_raises() -> None:
    store = _store_up_down()
    cfg = LabelConfig(horizon=timedelta(days=1), label_type=LabelType.FORWARD_RETURN, market_dataset_id="bars")
    with pytest.raises(LabelError, match="decision_times must be non-empty"):
        AsOfLabelEngine(store).compute(["AAA"], [], cfg)


# ---------------------------------------------------------------------------
# Insufficient price data -> LabelError
# ---------------------------------------------------------------------------

def test_insufficient_price_data_raises() -> None:
    # eligible but no price timeline -> latest_available returns empty
    elig = _eligibility([(_ts("2021-01-01T00:00:00Z"), "AAA")])
    store = _FakeAsOf(elig, {})
    cfg = LabelConfig(horizon=timedelta(days=1), label_type=LabelType.FORWARD_RETURN, market_dataset_id="bars")
    with pytest.raises(LabelError, match="insufficient price data"):
        AsOfLabelEngine(store).compute(["AAA"], [_ts("2021-01-01T00:00:00Z")], cfg)


# ---------------------------------------------------------------------------
# to_event_interval() bridge to SPLIT-001
# ---------------------------------------------------------------------------

def test_to_event_interval_bridge_to_split() -> None:
    store = _store_up_down()
    cfg = LabelConfig(horizon=timedelta(days=1), label_type=LabelType.FORWARD_RETURN, market_dataset_id="bars")
    events = AsOfLabelEngine(store).compute(
        ["AAA", "BBB"],
        [_ts("2021-01-01T00:00:00Z"), _ts("2021-01-02T00:00:00Z")],
        cfg,
    )
    intervals = [e.to_event_interval() for e in events]
    # Feed into SPLIT-001 purged K-fold to prove the bridge is structurally valid.
    split_cfg = SplitConfig(mode=SplitMode.PURGED_KFOLD, n_folds=2)
    folds = PurgedChronologicalSplitter(store).split(intervals, split_cfg)
    assert len(folds) >= 1
    # every fold's events came from labeled decision events
    total = sum(len(f.train.events) + len(f.test.events) for f in folds)
    assert total == len(intervals)
