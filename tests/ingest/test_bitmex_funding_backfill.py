"""Failure-path tests for the BitMEX funding backfill publication boundary."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.ingest.bitmex_funding import (
    BITMEX_FUNDING_SCHEMA,
    PROVENANCE_SOURCE,
    BitMEXFundingError,
    build_funding_table,
)

CODE_COMMIT = "0123456789abcdef0123456789abcdef01234567"
REPO = Path(__file__).resolve().parents[2]


def _load():
    script = REPO / "scripts" / "research" / "backfill_bitmex_funding.py"
    spec = importlib.util.spec_from_file_location("bitmex_backfill_review487", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _raw(symbol: str, timestamp: str, rate: float = 0.0001, daily: float = 0.0004) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "symbol": symbol,
        "fundingInterval": "2000-01-01T08:00:00.000Z",
        "fundingRate": rate,
        "fundingRateDaily": daily,
    }


def _stage(store: Path) -> Path:
    return store / "staged" / "bitmex_funding_full" / "funding.parquet"


def _write_stage(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(build_funding_table(records), path)


def _write_watermarks(path: Path, watermarks: dict[str, str]) -> None:
    path.write_text(
        json.dumps({"watermarks": watermarks}, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _signature(path: Path) -> tuple[Any, ...]:
    if not path.exists():
        return (None,)
    stat = path.stat()
    return (stat.st_ino, stat.st_size, path.read_bytes())


def _argv(tmp_path: Path, *extra: str) -> list[str]:
    return [
        "--db-path",
        str(tmp_path / "exp.db"),
        "--store-root",
        str(tmp_path / "store"),
        "--watermark-path",
        str(tmp_path / "watermarks.json"),
        "--report-path",
        str(tmp_path / "report.json"),
        "--code-commit",
        CODE_COMMIT,
        "--rate-per-minute",
        "100000",
        "--start-time",
        "2020-01-01T00:00:00+00:00",
        "--end-time",
        "2020-02-01T00:00:00+00:00",
        *extra,
    ]


_ORIGINAL_HTTPX_CLIENT = httpx.Client


def _patch_transport(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    import cryptofactors.ingest.bitmex_funding as funding

    transport = httpx.MockTransport(handler)

    def factory(*args, **kwargs):
        params = dict(kwargs)
        params["transport"] = transport
        return _ORIGINAL_HTTPX_CLIENT(*args, **params)

    monkeypatch.setattr(funding.httpx, "Client", factory)


def _seed_prior(
    tmp_path: Path,
    records: list[dict[str, Any]],
    watermarks: dict[str, str],
) -> tuple[Path, Path]:
    stage = _stage(tmp_path / "store")
    _write_stage(stage, records)
    watermark = tmp_path / "watermarks.json"
    _write_watermarks(watermark, watermarks)
    return stage, watermark


def _published_id(err: str) -> str:
    marker = "dataset_id="
    assert marker in err
    token = err.split(marker, 1)[1].split()[0].strip().rstrip(".,")
    assert token.startswith("ds_")
    assert "no rollback was performed" in err
    assert "before catalog registration" not in err
    return token


def _catalog_id(module, db_path: Path) -> str | None:
    catalog = module.SqliteDatasetCatalog(db_path)
    try:
        return catalog.resolve_latest_by_type(module.DATASET_TYPE)
    finally:
        catalog.close()


def _guard(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected request {request.url}")

    _patch_transport(monkeypatch, handler)


class _SpyPublisher:
    calls = 0

    def __init__(self, config, catalog) -> None:
        pass

    def publish(self, plan, register_catalog: bool = True):
        type(self).calls += 1
        raise RuntimeError("publisher should not run")


def test_inclusive_resume_keeps_explicit_bounds() -> None:
    module = _load()
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2020, 2, 1, tzinfo=timezone.utc)
    watermark = datetime(2020, 1, 15, tzinfo=timezone.utc)
    assert module.inclusive_resume_start(
        requested_start=start,
        requested_end=end,
        watermark=watermark,
    ) == watermark
    assert module.inclusive_resume_start(
        requested_start=datetime(2020, 1, 20, tzinfo=timezone.utc),
        requested_end=end,
        watermark=watermark,
    ) == datetime(2020, 1, 20, tzinfo=timezone.utc)
    assert (
        module.inclusive_resume_start(
            requested_start=start,
            requested_end=watermark,
            watermark=watermark,
        )
        is None
    )


def test_merge_collapses_identical_rows_and_rejects_conflicts() -> None:
    module = _load()
    prior = build_funding_table([_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001)]).to_pylist()
    same = build_funding_table([_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001)]).to_pylist()
    merged = module.merge_funding_records(prior, same)
    assert len(merged) == 1
    conflict = build_funding_table([_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0009)]).to_pylist()
    with pytest.raises(BitMEXFundingError, match="conflict"):
        module.merge_funding_records(prior, conflict)


def test_watermark_without_stage_does_not_publish(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load()
    _guard(monkeypatch)
    _SpyPublisher.calls = 0
    monkeypatch.setattr(module, "DatasetPublisher", _SpyPublisher)
    watermark = tmp_path / "watermarks.json"
    _write_watermarks(watermark, {"XBTUSD": "2020-01-01T00:00:00+00:00"})
    before = watermark.read_bytes()
    code = module.main(_argv(tmp_path, "--symbols", "XBTUSD"))
    assert code == 1
    assert _SpyPublisher.calls == 0
    assert watermark.read_bytes() == before
    assert not _stage(tmp_path / "store").exists()


def test_malformed_watermark_and_stage_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load()
    _guard(monkeypatch)
    _SpyPublisher.calls = 0
    monkeypatch.setattr(module, "DatasetPublisher", _SpyPublisher)
    watermark = tmp_path / "watermarks.json"
    watermark.write_text("{", encoding="utf-8")
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    stage = _stage(tmp_path / "store")
    _write_stage(stage, [_raw("XBTUSD", "2020-01-01T00:00:00Z")])
    before = stage.read_bytes()
    stage.write_bytes(b"not parquet")
    watermark.write_text(json.dumps({"watermarks": {}}), encoding="utf-8")
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    assert stage.read_bytes() == b"not parquet"
    assert before != stage.read_bytes()
    assert _SpyPublisher.calls == 0


def test_ahead_watermark_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load()
    _guard(monkeypatch)
    _SpyPublisher.calls = 0
    monkeypatch.setattr(module, "DatasetPublisher", _SpyPublisher)
    stage = _stage(tmp_path / "store")
    _write_stage(stage, [_raw("XBTUSD", "2020-01-01T00:00:00Z")])
    watermark = tmp_path / "watermarks.json"
    _write_watermarks(watermark, {"XBTUSD": "2020-01-02T00:00:00+00:00"})
    before_stage = _signature(stage)
    before_wm = _signature(watermark)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    assert _signature(stage) == before_stage
    assert _signature(watermark) == before_wm
    assert _SpyPublisher.calls == 0


def test_empty_refetch_of_known_event_does_not_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load()
    stage, watermark = _seed_prior(
        tmp_path,
        [_raw("XBTUSD", "2020-01-15T00:00:00Z", 0.0001, 0.0004)],
        {"XBTUSD": "2020-01-15T00:00:00+00:00"},
    )
    before_stage = _signature(stage)
    before_wm = _signature(watermark)
    seen: list[str] = []

    def empty(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=[])

    _patch_transport(monkeypatch, empty)
    _SpyPublisher.calls = 0
    monkeypatch.setattr(module, "DatasetPublisher", _SpyPublisher)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    err = capsys.readouterr().err
    assert "empty_requested_symbols" in err
    assert "XBTUSD" in err
    assert any("symbol=XBTUSD" in url and "/funding" in url for url in seen)
    assert _SpyPublisher.calls == 0
    assert _signature(stage) == before_stage
    assert _signature(watermark) == before_wm


def test_failed_symbol_fetch_does_not_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load()
    stage, watermark = _seed_prior(
        tmp_path,
        [_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004)],
        {"XBTUSD": "2020-01-01T00:00:00+00:00"},
    )
    before_stage = _signature(stage)
    before_wm = _signature(watermark)
    seen: list[str] = []

    def mixed(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "symbol=ETHUSD" in str(request.url):
            return httpx.Response(500, json={"error": "down"})
        return httpx.Response(200, json=[_raw("XBTUSD", "2020-01-01T04:00:00Z", 0.0002, 0.0004)])

    _patch_transport(monkeypatch, mixed)
    _SpyPublisher.calls = 0
    monkeypatch.setattr(module, "DatasetPublisher", _SpyPublisher)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD,ETHUSD")) == 1
    err = capsys.readouterr().err
    assert "HTTP 500" in err
    assert "ETHUSD" in err
    assert "empty_requested_symbols" not in err
    assert any("symbol=ETHUSD" in url for url in seen)
    assert any("symbol=XBTUSD" in url for url in seen)
    assert _SpyPublisher.calls == 0
    assert _signature(stage) == before_stage
    assert _signature(watermark) == before_wm


def test_invalid_candidate_and_publisher_failure_keep_prior_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load()
    stage = _stage(tmp_path / "store")
    _write_stage(stage, [_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001)])
    watermark = tmp_path / "watermarks.json"
    _write_watermarks(watermark, {"XBTUSD": "2020-01-01T00:00:00+00:00"})
    before_stage = _signature(stage)
    before_wm = _signature(watermark)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                _raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001),
                _raw("XBTUSD", "2020-01-01T01:00:00Z", 0.0002),
            ],
        )

    _patch_transport(monkeypatch, handler)

    def reject_candidate(path: Path, *, expected_rows: int):
        raise BitMEXFundingError("candidate parquet is invalid")

    monkeypatch.setattr(module, "validate_candidate_parquet", reject_candidate)
    _SpyPublisher.calls = 0
    monkeypatch.setattr(module, "DatasetPublisher", _SpyPublisher)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    assert _SpyPublisher.calls == 0
    assert _signature(stage) == before_stage
    assert _signature(watermark) == before_wm

    monkeypatch.undo()
    _patch_transport(monkeypatch, handler)

    class BoomPublisher:
        calls = 0

        def __init__(self, config, catalog) -> None:
            pass

        def publish(self, plan, register_catalog: bool = True):
            type(self).calls += 1
            raise RuntimeError("publisher failed")

    monkeypatch.setattr(module, "DatasetPublisher", BoomPublisher)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    assert BoomPublisher.calls == 1
    assert _signature(stage) == before_stage
    assert _signature(watermark) == before_wm


def test_publication_precedes_stage_and_keeps_sub_hour_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load()
    stage = _stage(tmp_path / "store")
    _write_stage(
        stage,
        [
            _raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004),
            _raw("ETHUSD", "2020-01-01T00:00:00Z", 0.0002, 0.0004),
        ],
    )
    watermark = tmp_path / "watermarks.json"
    _write_watermarks(
        watermark,
        {
            "ETHUSD": "2020-01-01T00:00:00+00:00",
            "XBTUSD": "2020-01-01T00:00:00+00:00",
        },
    )
    before_stage = stage.read_bytes()
    before_wm = watermark.read_bytes()
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params["startTime"])
        return httpx.Response(
            200,
            json=[
                _raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004),
                _raw("XBTUSD", "2020-01-01T01:00:00Z", 0.0003, 0.0004),
            ],
        )

    _patch_transport(monkeypatch, handler)
    real_publisher = module.DatasetPublisher
    published = {"ok": False}

    class Wrapped:
        def __init__(self, config, catalog) -> None:
            self._inner = real_publisher(config, catalog)

        def publish(self, plan, register_catalog: bool = True):
            assert stage.read_bytes() == before_stage
            assert watermark.read_bytes() == before_wm
            published["ok"] = True
            return self._inner.publish(plan, register_catalog=register_catalog)

    monkeypatch.setattr(module, "DatasetPublisher", Wrapped)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 0
    assert published["ok"] is True
    assert seen == ["2020-01-01T00:00:00.000000Z"]
    rows = pq.read_table(stage).to_pylist()
    assert any(row["symbol"] == "XBTUSD" and row["timestamp"].startswith("2020-01-01T01:00:00") for row in rows)
    assert any(row["symbol"] == "ETHUSD" for row in rows)
    saved = json.loads(watermark.read_text(encoding="utf-8"))["watermarks"]
    assert saved["ETHUSD"].startswith("2020-01-01T00:00:00")
    assert saved["XBTUSD"].startswith("2020-01-01T01:00:00")
    assert stage.read_bytes() != before_stage


def test_conflicting_overlap_does_not_publish(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load()
    stage = _stage(tmp_path / "store")
    _write_stage(stage, [_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004)])
    watermark = tmp_path / "watermarks.json"
    _write_watermarks(watermark, {"XBTUSD": "2020-01-01T00:00:00+00:00"})
    before_stage = _signature(stage)
    before_wm = _signature(watermark)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0009, 0.0004)])

    _patch_transport(monkeypatch, handler)
    _SpyPublisher.calls = 0
    monkeypatch.setattr(module, "DatasetPublisher", _SpyPublisher)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    assert _SpyPublisher.calls == 0
    assert _signature(stage) == before_stage
    assert _signature(watermark) == before_wm


def test_post_publication_failures_keep_the_dataset_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load()
    stage = _stage(tmp_path / "store")
    _write_stage(stage, [_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004)])
    watermark = tmp_path / "watermarks.json"
    _write_watermarks(watermark, {"XBTUSD": "2020-01-01T00:00:00+00:00"})
    before_stage = stage.read_bytes()
    before_wm = watermark.read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                _raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004),
                _raw("XBTUSD", "2020-01-01T01:00:00Z", 0.0003, 0.0004),
            ],
        )

    _patch_transport(monkeypatch, handler)

    def boom_promote(*args, **kwargs):
        raise OSError("stage replace failed")

    monkeypatch.setattr(module, "promote_candidate", boom_promote)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    err = capsys.readouterr().err
    assert "dataset_id=" in err
    assert "no rollback was performed" in err
    assert "before catalog registration" not in err
    assert stage.read_bytes() == before_stage
    assert watermark.read_bytes() == before_wm

    monkeypatch.undo()
    _patch_transport(monkeypatch, handler)

    def boom_resolve(self, dataset_type: str, *, consumable_only: bool = True):
        raise RuntimeError("resolver failed")

    monkeypatch.setattr(module.SqliteDatasetCatalog, "resolve_latest_by_type", boom_resolve)
    assert module.main(_argv(tmp_path / "resolve", "--symbols", "XBTUSD")) == 1
    err = capsys.readouterr().err
    assert "dataset_id=" in err
    assert "no rollback was performed" in err
    assert "before catalog registration" not in err


def test_legacy_all_zero_stage_is_not_reset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load()
    _guard(monkeypatch)
    _SpyPublisher.calls = 0
    monkeypatch.setattr(module, "DatasetPublisher", _SpyPublisher)
    stage = _stage(tmp_path / "store")
    stage.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "timestamp": ["2020-01-01T00:00:00Z", "2020-01-01T01:00:00Z"],
            "timestamp_us": [1577836800000000, 1577840400000000],
            "symbol": ["XBTUSD", "XBTUSD"],
            "funding_rate": [0.0, 0.0],
            "funding_rate_daily": [0.0, 0.0],
            "funding_interval": ["2000-01-01T08:00:00Z", "2000-01-01T08:00:00Z"],
            "source": [PROVENANCE_SOURCE, PROVENANCE_SOURCE],
            "availability_time": [None, None],
        },
        schema=BITMEX_FUNDING_SCHEMA,
    )
    pq.write_table(table, stage)
    before = stage.read_bytes()
    _write_watermarks(tmp_path / "watermarks.json", {"XBTUSD": "2020-01-01T00:00:00+00:00"})
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    assert stage.read_bytes() == before
    assert _SpyPublisher.calls == 0


def test_duplicate_symbol_argument_is_unique() -> None:
    module = _load()
    assert module.unique_symbols(["XBTUSD", "ETHUSD", "XBTUSD"]) == ["XBTUSD", "ETHUSD"]
    assert module.missing_requested_symbols(["XBTUSD"], []) == ["XBTUSD"]
    assert module.FUNDING_SCHEMA_NAME == "bitmex_funding"
    assert module.FUNDING_SCHEMA_VERSION == "1"
    assert module.FUNDING_SCHEMA_FINGERPRINT == "fund_v1"
    assert module.FUNDING_TRANSFORM_NAME == "bitmex_funding_full_backfill"
    assert module.FUNDING_TRANSFORM_VERSION == "1"


def test_resume_does_not_add_eight_hours() -> None:
    module = _load()
    watermark = datetime(2020, 1, 1, 0, 0, tzinfo=timezone.utc)
    start = module.inclusive_resume_start(
        requested_start=datetime(2016, 5, 13, tzinfo=timezone.utc),
        requested_end=datetime(2020, 2, 1, tzinfo=timezone.utc),
        watermark=watermark,
    )
    assert start == watermark
    assert start != watermark + timedelta(hours=8)


def test_in_window_presence_does_not_infer_cadence() -> None:
    module = _load()
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2020, 2, 1, tzinfo=timezone.utc)
    inside = build_funding_table([_raw("XBTUSD", "2020-01-15T00:00:00Z")]).to_pylist()
    assert module.symbols_missing_in_window(
        ["XBTUSD"],
        inside,
        requested_start=start,
        requested_end=end,
    ) == []
    future = build_funding_table([_raw("XBTUSD", "2020-03-01T00:00:00Z")]).to_pylist()
    assert module.symbols_missing_in_window(
        ["XBTUSD"],
        future,
        requested_start=start,
        requested_end=end,
    ) == ["XBTUSD"]
    sparse = build_funding_table(
        [
            _raw("ETHUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004),
            _raw("ETHUSD", "2020-01-01T01:00:00Z", 0.0002, 0.0004),
        ]
    ).to_pylist()
    assert module.symbols_missing_in_window(
        ["ETHUSD"],
        sparse,
        requested_start=start,
        requested_end=end,
    ) == []


def test_future_only_skip_is_not_window_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load()
    stage, watermark = _seed_prior(
        tmp_path,
        [_raw("XBTUSD", "2020-03-01T00:00:00Z", 0.0001, 0.0004)],
        {"XBTUSD": "2020-03-01T00:00:00+00:00"},
    )
    before_stage = _signature(stage)
    before_wm = _signature(watermark)
    _guard(monkeypatch)
    _SpyPublisher.calls = 0
    monkeypatch.setattr(module, "DatasetPublisher", _SpyPublisher)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    err = capsys.readouterr().err
    assert "missing_in_window_coverage" in err
    assert "XBTUSD" in err
    assert _SpyPublisher.calls == 0
    assert _signature(stage) == before_stage
    assert _signature(watermark) == before_wm
    assert not (tmp_path / "report.json").exists()


def test_skipped_boundary_event_publishes_without_fetch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load()
    _seed_prior(
        tmp_path,
        [_raw("XBTUSD", "2020-02-01T00:00:00Z", 0.0001, 0.0004)],
        {"XBTUSD": "2020-02-01T00:00:00+00:00"},
    )
    _guard(monkeypatch)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 0
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["row_count"] == 1
    assert report["symbols_skipped_current"] == ["XBTUSD"]
    assert report["dataset_id"].startswith("ds_")
    assert report["dataset_id"] == _catalog_id(module, tmp_path / "exp.db")
    saved = json.loads((tmp_path / "watermarks.json").read_text(encoding="utf-8"))
    assert saved["watermarks"]["XBTUSD"].startswith("2020-02-01T00:00:00")


def test_watermark_precision_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load()
    for text in (
        "2020-01-01T00:00:00,1234561+00:00",
        "2020-01-01T00:00:00,123456+00:00",
        "2020-01-01T00:00:00+00:00.1234561",
        "2020-01-01T00:00:00+00:00.1",
    ):
        with pytest.raises(BitMEXFundingError, match="unsupported timestamp syntax"):
            module.parse_strict_watermark(text)
    with pytest.raises(BitMEXFundingError, match="not representable"):
        module.parse_strict_watermark("2020-01-01T00:00:00.1234561Z")
    parsed = module.parse_strict_watermark("2020-01-01T00:00:00.123456000Z")
    assert parsed.microsecond == 123456

    stage, watermark = _seed_prior(
        tmp_path,
        [_raw("XBTUSD", "2020-01-01T00:00:00.123456Z", 0.0001, 0.0004)],
        {"XBTUSD": "2020-01-01T00:00:00.1234561+00:00"},
    )
    before_stage = _signature(stage)
    before_wm = _signature(watermark)
    _guard(monkeypatch)
    _SpyPublisher.calls = 0
    monkeypatch.setattr(module, "DatasetPublisher", _SpyPublisher)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    assert "not representable" in capsys.readouterr().err
    assert _SpyPublisher.calls == 0
    assert _signature(stage) == before_stage
    assert _signature(watermark) == before_wm


def _extend_xbt(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json=[
            _raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004),
            _raw("XBTUSD", "2020-01-01T01:00:00Z", 0.0003, 0.0004),
        ],
    )


def test_candidate_fsync_failure_does_not_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load()
    stage, watermark = _seed_prior(
        tmp_path,
        [_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004)],
        {"XBTUSD": "2020-01-01T00:00:00+00:00"},
    )
    before_stage = _signature(stage)
    before_wm = _signature(watermark)
    _patch_transport(monkeypatch, _extend_xbt)

    def boom(path: Path) -> None:
        raise OSError("candidate fsync failed")

    monkeypatch.setattr(module, "fsync_path", boom)
    _SpyPublisher.calls = 0
    monkeypatch.setattr(module, "DatasetPublisher", _SpyPublisher)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    err = capsys.readouterr().err
    assert "before catalog registration" in err
    assert "catalog publication succeeded" not in err
    assert _SpyPublisher.calls == 0
    assert _signature(stage) == before_stage
    assert _signature(watermark) == before_wm


def test_stage_directory_barrier_prevents_watermark_advance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load()
    stage, watermark = _seed_prior(
        tmp_path,
        [_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004)],
        {"XBTUSD": "2020-01-01T00:00:00+00:00"},
    )
    before_wm = watermark.read_bytes()
    _patch_transport(monkeypatch, _extend_xbt)
    real_fsync = module.fsync_path
    stage_dir = stage.parent.resolve()

    def selective(path: Path) -> None:
        if Path(path).resolve() == stage_dir:
            raise OSError("stage directory barrier failed")
        real_fsync(path)

    monkeypatch.setattr(module, "fsync_path", selective)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    err = capsys.readouterr().err
    published = _published_id(err)
    assert published == _catalog_id(module, tmp_path / "exp.db")
    assert watermark.read_bytes() == before_wm
    assert not (tmp_path / "report.json").exists()


def test_watermark_directory_barrier_is_after_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load()
    _seed_prior(
        tmp_path,
        [_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004)],
        {"XBTUSD": "2020-01-01T00:00:00+00:00"},
    )
    _patch_transport(monkeypatch, _extend_xbt)
    real_fsync = module.fsync_path
    watermark_dir = (tmp_path / "watermarks.json").parent.resolve()

    def selective(path: Path) -> None:
        if Path(path).resolve() == watermark_dir:
            raise OSError("watermark directory barrier failed")
        real_fsync(path)

    monkeypatch.setattr(module, "fsync_path", selective)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    err = capsys.readouterr().err
    published = _published_id(err)
    assert published == _catalog_id(module, tmp_path / "exp.db")
    saved = json.loads((tmp_path / "watermarks.json").read_text(encoding="utf-8"))
    assert saved["watermarks"]["XBTUSD"].startswith("2020-01-01T01:00:00")
    assert not (tmp_path / "report.json").exists()


def test_post_publication_watermark_report_and_close_keep_dataset_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load()
    _seed_prior(
        tmp_path,
        [_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004)],
        {"XBTUSD": "2020-01-01T00:00:00+00:00"},
    )
    before_wm = (tmp_path / "watermarks.json").read_bytes()
    _patch_transport(monkeypatch, _extend_xbt)

    def boom_watermarks(*args, **kwargs):
        raise OSError("watermark replace failed")

    monkeypatch.setattr(module, "save_watermarks", boom_watermarks)
    assert module.main(_argv(tmp_path, "--symbols", "XBTUSD")) == 1
    err = capsys.readouterr().err
    published = _published_id(err)
    assert published == _catalog_id(module, tmp_path / "exp.db")
    assert (tmp_path / "watermarks.json").read_bytes() == before_wm

    monkeypatch.undo()
    report_root = tmp_path / "report-fail"
    _seed_prior(
        report_root,
        [_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004)],
        {"XBTUSD": "2020-01-01T00:00:00+00:00"},
    )
    _patch_transport(monkeypatch, _extend_xbt)

    def boom_report(*args, **kwargs):
        raise OSError("report replace failed")

    monkeypatch.setattr(module, "write_json_report", boom_report)
    assert module.main(_argv(report_root, "--symbols", "XBTUSD")) == 1
    err = capsys.readouterr().err
    published = _published_id(err)
    assert published == _catalog_id(module, report_root / "exp.db")
    assert not (report_root / "report.json").exists()

    monkeypatch.undo()
    close_root = tmp_path / "close-fail"
    stage, watermark = _seed_prior(
        close_root,
        [_raw("XBTUSD", "2020-01-01T00:00:00Z", 0.0001, 0.0004)],
        {"XBTUSD": "2020-01-01T00:00:00+00:00"},
    )
    before_stage = stage.read_bytes()
    before_close_wm = watermark.read_bytes()
    _patch_transport(monkeypatch, _extend_xbt)
    original_close = module.SqliteDatasetCatalog.close

    def boom_close(self) -> None:
        raise RuntimeError("catalog close failed")

    monkeypatch.setattr(module.SqliteDatasetCatalog, "close", boom_close)
    assert module.main(_argv(close_root, "--symbols", "XBTUSD")) == 1
    err = capsys.readouterr().err
    published = _published_id(err)
    catalog = module.SqliteDatasetCatalog(close_root / "exp.db")
    try:
        assert catalog.resolve_latest_by_type(module.DATASET_TYPE) == published
    finally:
        original_close(catalog)
    assert stage.read_bytes() == before_stage
    assert watermark.read_bytes() == before_close_wm
