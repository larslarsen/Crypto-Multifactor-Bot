from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import sqlite3
import zipfile
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path, PurePosixPath

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import cryptofactors.ingest.binance_usdm_cost_calibration as subject
from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    cost_manifest_digest,
)
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    COST_COMPONENTS,
    PRODUCT_COST_CALIBRATION,
    cost_component_columns,
    fee_scenario_rows,
    product_schema_identity,
)


def _zip(member: str, rows: list[list[str]], *, header: list[str] | None = None) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    if header is not None:
        writer.writerow(header)
    writer.writerows(rows)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, stream.getvalue())
    return output.getvalue()


def _raw(
    tmp_path: Path,
    *,
    family: str,
    symbol: str,
    day: str,
    rows: list[list[str]],
    headed: bool = False,
    authority: str = "accepted_generation_0_completion",
) -> subject.RawCostObject:
    kind = family.rsplit("/", 1)[1]
    basename = f"{symbol}-{kind}-{day}"
    fields = subject.KNOWN_ARCHIVE_SCHEMAS[kind]["headerless"]
    body = _zip(f"{basename}.csv", rows, header=list(fields) if headed else None)
    digest = hashlib.sha256(body).hexdigest()
    path = tmp_path / digest
    path.write_bytes(body)
    return subject.RawCostObject(
        source_key=f"data/futures/um/daily/{kind}/{symbol}/{basename}.zip",
        family=family,
        native_symbol=symbol,
        economic_day=day,
        path=path,
        source_sha256=digest,
        byte_size=len(body),
        etag="etag",
        authority=authority,
        checksum_authority="binance_checksum_sidecar",
        retrieval_time=(
            "2026-08-31T00:00:00+00:00"
            if authority == "accepted_generation_0_completion"
            else None
        ),
    )


def _identity(symbol: str) -> subject.MembershipIdentity:
    return subject.MembershipIdentity(
        "BINANCE_USDM",
        symbol,
        None,
        None,
        "reference_identity_not_yet_created",
    )


def _ticker_rows() -> list[list[str]]:
    return [
        ["1", "100.000000000000000001", "2", "101", "3", "1609459199999", "1609459199000"],
        ["2", "100", "1", "0E-8", "0", "1609459200000", "1609459200000"],
        ["3", "0", "0", "102", "0", "1609459200000", "1609459200000"],
        ["4", "0", "0", "0", "0", "1609459200000", "1609459200000"],
    ]


def _depth_rows() -> list[list[str]]:
    return [
        ["2021-01-01 00:00:00", "-5", "0", "0"],
        ["2021-01-01 00:00:00", "-4", "1.000000000000000001", "2"],
        ["2021-01-01 00:00:00", "-3", "2", "3"],
    ]


def _normalize(tmp_path: Path, *, hooks: subject.PublicationHooks = subject.PublicationHooks()) -> subject.CostCalibrationResult:
    ticker = _raw(
        tmp_path,
        family=subject.FAMILY_TICKER,
        symbol="BTCUSDT",
        day="2020-12-31",
        rows=_ticker_rows(),
        headed=True,
    )
    depth = _raw(
        tmp_path,
        family=subject.FAMILY_DEPTH,
        symbol="XCNUSDT",
        day="2021-01-01",
        rows=_depth_rows(),
    )
    return subject.normalize_cost_sources(
        [ticker, depth],
        [_identity("BTCUSDT"), _identity("XCNUSDT")],
        [
            {
                "blocking": True,
                "family": subject.FAMILY_TICKER,
                "family_group": "bookTicker",
                "kind": "cost_sample_unavailable",
                "status": "cost_sample_unavailable",
                "symbol": "XCNUSDT",
            }
        ],
        tmp_path / ".cost",
        hooks=hooks,
    )


def test_exact_fiveogeneous_component_schemas() -> None:
    assert tuple(subject.SCHEMAS) == COST_COMPONENTS
    assert subject.SCHEMA_SHA256 == product_schema_identity(PRODUCT_COST_CALIBRATION)
    for component in COST_COMPONENTS:
        assert subject.SCHEMAS[component] == pa.schema(
            [column.field() for column in cost_component_columns(component)]
        )


def test_headed_ticker_preserves_exact_fields_ordinals_states_and_month_boundary(
    tmp_path: Path,
) -> None:
    source = _raw(
        tmp_path,
        family=subject.FAMILY_TICKER,
        symbol="BTCUSDT",
        day="2020-12-31",
        rows=_ticker_rows(),
        headed=True,
    )
    rows = []
    states = []
    for ordinal, cells in subject._member(source):
        values, month, state = subject._typed_row(
            source, 7, ordinal, cells, _identity("BTCUSDT")
        )
        rows.append((values, month))
        states.append(state)
    assert [row[0]["source_row_ordinal"] for row in rows] == [0, 1, 2, 3]
    assert rows[0][0]["best_bid_price"] == Decimal("100.000000000000000001")
    assert [month for _row, month in rows] == ["2020-12", "2021-01", "2021-01", "2021-01"]
    assert states == ["two_sided", "bid_only", "ask_only", "empty"]


def test_headerless_depth_preserves_signed_bands_zero_depth_and_repeated_times(
    tmp_path: Path,
) -> None:
    source = _raw(
        tmp_path,
        family=subject.FAMILY_DEPTH,
        symbol="XCNUSDT",
        day="2021-01-01",
        rows=_depth_rows(),
    )
    parsed = [
        subject._typed_row(source, 0, ordinal, cells, _identity("XCNUSDT"))[0]
        for ordinal, cells in subject._member(source)
    ]
    assert [row["source_row_ordinal"] for row in parsed] == [0, 1, 2]
    assert [row["percentage"] for row in parsed] == [Decimal("-5"), Decimal("-4"), Decimal("-3")]
    assert len({row["timestamp"] for row in parsed}) == 1
    assert parsed[0]["depth"] == Decimal("0")


def test_decimal_conversion_is_independent_of_ambient_context(tmp_path: Path) -> None:
    source = _raw(
        tmp_path,
        family=subject.FAMILY_TICKER,
        symbol="BTCUSDT",
        day="2020-12-31",
        rows=[_ticker_rows()[0]],
    )
    ordinal, cells = next(subject._member(source))
    with localcontext() as context:
        context.prec = 3
        low = subject._typed_row(source, 0, ordinal, cells, _identity("BTCUSDT"))[0]
    with localcontext() as context:
        context.prec = 38
        high = subject._typed_row(source, 0, ordinal, cells, _identity("BTCUSDT"))[0]
    assert low == high


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda rows: [[*rows[0][:1], "-1", *rows[0][2:]]], "negative"),
        (lambda rows: [[rows[0][0], "2", "1", "1", "1", *rows[0][5:]]], "crossed"),
        (lambda rows: [[rows[0][0], "0", "1", *rows[0][3:]]], "inconsistent"),
        (lambda rows: [[rows[0][0], "NaN", *rows[0][2:]]], "invalid"),
    ],
)
def test_invalid_ticker_values_refuse(
    tmp_path: Path,
    mutator: object,
    message: str,
) -> None:
    rows = mutator(_ticker_rows())  # type: ignore[operator]
    source = _raw(
        tmp_path,
        family=subject.FAMILY_TICKER,
        symbol="BTCUSDT",
        day="2020-12-31",
        rows=rows,
    )
    ordinal, cells = next(subject._member(source))
    with pytest.raises(subject.CostCalibrationError, match=message):
        subject._typed_row(source, 0, ordinal, cells, _identity("BTCUSDT"))


@pytest.mark.parametrize(
    "cells",
    [
        ["2021-01-01 00:00:00", "0", "1", "1"],
        ["2021-01-01 00:00:00", "-5", "-1", "1"],
        ["bad-time", "-5", "1", "1"],
    ],
)
def test_invalid_depth_values_refuse(tmp_path: Path, cells: list[str]) -> None:
    source = _raw(
        tmp_path,
        family=subject.FAMILY_DEPTH,
        symbol="XCNUSDT",
        day="2021-01-01",
        rows=[cells],
    )
    ordinal, row = next(subject._member(source))
    with pytest.raises(subject.CostCalibrationError):
        subject._typed_row(source, 0, ordinal, row, _identity("XCNUSDT"))


def test_source_day_boundary_allows_exact_next_midnight_and_refuses_later(
    tmp_path: Path,
) -> None:
    source = _raw(
        tmp_path,
        family=subject.FAMILY_TICKER,
        symbol="BTCUSDT",
        day="2020-12-31",
        rows=[_ticker_rows()[1]],
    )
    ordinal, cells = next(subject._member(source))
    _values, month, _state = subject._typed_row(
        source, 0, ordinal, cells, _identity("BTCUSDT")
    )
    assert month == "2021-01"
    cells[-2] = "1609459200001"
    with pytest.raises(subject.CostCalibrationError, match="source day boundary"):
        subject._typed_row(source, 0, ordinal, cells, _identity("BTCUSDT"))


def test_zip_hash_member_and_shape_fail_closed(tmp_path: Path) -> None:
    source = _raw(
        tmp_path,
        family=subject.FAMILY_DEPTH,
        symbol="XCNUSDT",
        day="2021-01-01",
        rows=_depth_rows(),
    )
    with pytest.raises(subject.CostCalibrationError, match="bytes changed"):
        list(subject._member(replace(source, source_sha256="0" * 64)))
    source.path.write_bytes(b"not a zip")
    corrupted = replace(
        source,
        source_sha256=hashlib.sha256(b"not a zip").hexdigest(),
        byte_size=len(b"not a zip"),
    )
    with pytest.raises(subject.CostCalibrationError, match="ZIP/CSV"):
        list(subject._member(corrupted))


def test_unsafe_and_multi_member_zip_refuse(tmp_path: Path) -> None:
    source = _raw(
        tmp_path,
        family=subject.FAMILY_DEPTH,
        symbol="XCNUSDT",
        day="2021-01-01",
        rows=_depth_rows(),
    )
    for names in (["../bad.csv"], ["one.csv", "two.csv"]):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name in names:
                archive.writestr(name, "1,-1,0,0\n")
        body = buffer.getvalue()
        source.path.write_bytes(body)
        changed = replace(
            source,
            source_sha256=hashlib.sha256(body).hexdigest(),
            byte_size=len(body),
        )
        with pytest.raises(subject.CostCalibrationError):
            list(subject._member(changed))


def test_product_has_all_five_components_and_honest_fee_semantics(tmp_path: Path) -> None:
    result = _normalize(tmp_path)
    assert {item.component for item in result.components} == set(COST_COMPONENTS)
    official = next(
        item for item in result.components if item.component == subject.COMPONENT_OFFICIAL_FEE
    )
    assert official.row_count == 0
    assert pq.ParquetFile(official.parquet_path).schema_arrow == subject.SCHEMAS[subject.COMPONENT_OFFICIAL_FEE]
    fee_gaps = [item for item in result.components if item.component == subject.COMPONENT_FEE_GAP]
    assert len(fee_gaps) == 2 and all(item.row_count == 1 for item in fee_gaps)
    scenarios = next(item for item in result.components if item.component == subject.COMPONENT_SCENARIO)
    rows = pq.read_table(scenarios.parquet_path).to_pylist()
    assert rows == list(fee_scenario_rows())
    assert all(row["authority_class"] == "ASSUMED_CONSERVATIVE" for row in rows)
    assert all(row["charges_each_side"] and not row["maker_credit_enabled"] for row in rows)


def test_completion_reconciles_rows_gaps_policy_and_lineage(tmp_path: Path) -> None:
    result = _normalize(tmp_path)
    completion = json.loads(result.completion_path.read_text())
    assert completion["source_equation"]["physical_rows"] == 7
    assert completion["source_equation"]["dropped_rows"] == 0
    assert completion["source_equation"]["physical_rows"] == sum(
        item["physical_rows"] for item in completion["source_row_reconciliation"]
    )
    assert all(
        item["physical_rows"] == item["retained_rows"]
        for item in completion["source_row_reconciliation"]
    )
    assert completion["component_rows"] == {
        "retained_book_ticker": 4,
        "retained_book_depth": 3,
        "official_fee_schedule": 0,
        "fee_authority_gap": 2,
        "scenario_policy": 2,
    }
    assert completion["quote_states"] == {
        "ask_only": 1,
        "bid_only": 1,
        "empty": 1,
        "two_sided": 1,
    }
    assert completion["fee_authority"]["missing_fee_is_zero"] is False
    assert completion["scenario_policy"]["historical_observation"] is False
    assert completion["frozen_source_gaps"]["row_count"] == 1
    measured = completion["measured_output_bytes"]
    assert measured["total"] == (
        measured["parquet"]
        + measured["lineage"]
        + measured["source_gaps"]
        + measured["completion"]
    )
    assert all(item.lineage_path.exists() for item in result.components)


def test_partition_writer_batches_and_does_not_materialize_full_partition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subject, "SIZING_ROW_BATCH", 2)
    observed: list[int] = []
    result = _normalize(
        tmp_path,
        hooks=subject.PublicationHooks(observe_batch=lambda _component, count: observed.append(count)),
    )
    assert result.source_rows == 7
    assert observed and max(observed) <= 2


def test_physical_ordinals_reconcile_once_across_objects_and_month_boundary(
    tmp_path: Path,
) -> None:
    boundary = _raw(
        tmp_path,
        family=subject.FAMILY_TICKER,
        symbol="BTCUSDT",
        day="2020-12-31",
        rows=_ticker_rows()[:2],
    )
    january = _raw(
        tmp_path,
        family=subject.FAMILY_TICKER,
        symbol="BTCUSDT",
        day="2021-01-01",
        rows=[["5", "100", "1", "101", "1", "1609459200001", "1609459200001"]],
    )
    result = subject.normalize_cost_sources(
        [january, boundary],
        [_identity("BTCUSDT")],
        [],
        tmp_path / ".cost",
    )
    completion = json.loads(result.completion_path.read_text())
    facts = {
        item["source_key"]: item for item in completion["source_row_reconciliation"]
    }
    assert completion["source_equation"]["physical_rows"] == 3
    assert completion["source_equation"]["retained_rows"] == 3
    assert facts[boundary.source_key]["partition_ranges"] == [
        {"first": 0, "last": 0},
        {"first": 1, "last": 1},
    ]
    assert facts[january.source_key]["partition_ranges"] == [
        {"first": 0, "last": 0}
    ]


def test_measured_output_refuses_reduced_allocation_before_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subject, "NORMALIZED_ALLOCATION_BYTES", 1)
    with pytest.raises(subject.CostCalibrationError, match="normalized allocation"):
        _normalize(tmp_path)
    completion = tmp_path / ".cost" / ".complete"
    assert not completion.exists() or not list(completion.iterdir())


def test_replay_is_byte_identical_and_completion_is_sole(tmp_path: Path) -> None:
    first = _normalize(tmp_path)
    second = _normalize(tmp_path)
    assert second.completion_sha256 == first.completion_sha256
    assert second.completion_reused is True
    assert all(item.reused for item in second.components)
    assert len(list((tmp_path / ".cost" / ".complete").iterdir())) == 1
    files = {
        str(path.relative_to(tmp_path / ".cost"))
        for path in (tmp_path / ".cost").rglob("*")
        if path.is_file()
    }
    assert len(files) == 2 * len(second.components) + 2
    assert not list((tmp_path / ".cost" / ".staging").iterdir())


def test_interruption_leaves_no_completion_and_resume_succeeds(tmp_path: Path) -> None:
    fired = False

    def stop(kind: str, _stage: Path, _destination: Path) -> None:
        nonlocal fired
        if not fired and kind == "lineage":
            fired = True
            raise RuntimeError("interrupt")

    with pytest.raises(RuntimeError, match="interrupt"):
        _normalize(tmp_path, hooks=subject.PublicationHooks(before_publish=stop))
    completion = tmp_path / ".cost" / ".complete"
    assert not completion.exists() or not list(completion.iterdir())
    assert not list((tmp_path / ".cost" / ".staging").iterdir())
    resumed = _normalize(tmp_path)
    assert resumed.source_rows == 7


def test_existing_different_completion_refuses(tmp_path: Path) -> None:
    completion = tmp_path / ".cost" / ".complete"
    completion.mkdir(parents=True)
    (completion / ("f" * 64 + ".json")).write_text("{}")
    with pytest.raises(subject.CostCalibrationError, match="another completion"):
        _normalize(tmp_path)


def test_symlinked_source_and_output_refuse(tmp_path: Path) -> None:
    source = _raw(
        tmp_path,
        family=subject.FAMILY_DEPTH,
        symbol="XCNUSDT",
        day="2021-01-01",
        rows=_depth_rows(),
    )
    target = source.path
    alias = tmp_path / "alias"
    alias.symlink_to(target)
    with pytest.raises(subject.CostCalibrationError, match="symlink"):
        list(subject._member(replace(source, path=alias)))
    root = tmp_path / ".linked"
    root.symlink_to(tmp_path / ".elsewhere")
    with pytest.raises(subject.CostCalibrationError, match="symlink"):
        subject._OutputTree(root)


@pytest.mark.parametrize("foreign_kind", ["file", "symlink"])
def test_completion_refuses_unreferenced_output_objects(
    tmp_path: Path, foreign_kind: str
) -> None:
    root = tmp_path / ".cost"
    root.mkdir()
    foreign = root / "foreign"
    if foreign_kind == "file":
        foreign.write_bytes(b"unreferenced")
    else:
        target = tmp_path / "target"
        target.write_bytes(b"outside")
        foreign.symlink_to(target)
    with pytest.raises(subject.CostCalibrationError, match="output"):
        _normalize(tmp_path)
    completion = root / ".complete"
    assert not completion.exists() or not list(completion.iterdir())


@pytest.mark.parametrize("mutation", ["corrupt", "missing", "symlink"])
def test_final_reproof_refuses_changed_published_partition(
    tmp_path: Path, mutation: str
) -> None:
    partition: Path | None = None
    changed = False

    def mutate(kind: str, _stage: Path, destination: Path) -> None:
        nonlocal partition, changed
        if kind == "partition" and partition is None:
            partition = destination
        elif kind == "lineage" and partition is not None and not changed:
            changed = True
            if mutation == "corrupt":
                partition.write_bytes(b"changed")
            elif mutation == "missing":
                partition.unlink()
            else:
                target = tmp_path / "replacement"
                target.write_bytes(b"replacement")
                partition.unlink()
                partition.symlink_to(target)

    with pytest.raises(subject.CostCalibrationError, match="published"):
        _normalize(
            tmp_path,
            hooks=subject.PublicationHooks(before_publish=mutate),
        )
    completion = tmp_path / ".cost" / ".complete"
    assert not completion.exists() or not list(completion.iterdir())


def test_held_stage_replacement_refuses_without_publishing_replacement(
    tmp_path: Path,
) -> None:
    replacement: Path | None = None
    destination: Path | None = None

    def replace_stage(kind: str, stage: Path, final: Path) -> None:
        nonlocal replacement, destination
        if kind == "partition" and replacement is None:
            stage.unlink()
            stage.write_bytes(b"foreign replacement")
            replacement = stage
            destination = final

    with pytest.raises(subject.CostCalibrationError, match="staged object was replaced"):
        _normalize(
            tmp_path,
            hooks=subject.PublicationHooks(before_publish=replace_stage),
        )
    assert replacement is not None and replacement.read_bytes() == b"foreign replacement"
    assert destination is not None and not destination.exists()


def test_conflicting_existing_content_is_not_clobbered(tmp_path: Path) -> None:
    conflict: Path | None = None

    def install_conflict(kind: str, _stage: Path, destination: Path) -> None:
        nonlocal conflict
        if kind == "partition" and conflict is None:
            destination.write_bytes(b"conflict")
            conflict = destination

    with pytest.raises(subject.CostCalibrationError, match="replay.*differ"):
        _normalize(
            tmp_path,
            hooks=subject.PublicationHooks(before_publish=install_conflict),
        )
    assert conflict is not None and conflict.read_bytes() == b"conflict"


def test_verified_staged_partition_is_renamed_without_copy(tmp_path: Path) -> None:
    observed: tuple[Path, int] | None = None

    def capture(kind: str, stage: Path, destination: Path) -> None:
        nonlocal observed
        if kind == "partition" and observed is None:
            observed = (destination, stage.stat().st_ino)

    _normalize(
        tmp_path,
        hooks=subject.PublicationHooks(before_publish=capture),
    )
    assert observed is not None
    destination, staged_inode = observed
    assert destination.stat().st_ino == staged_inode


def test_manifest_reproof_binds_full_union_and_gaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = [
        _raw(
            tmp_path,
            family=subject.FAMILY_TICKER,
            symbol="BTCUSDT",
            day="2020-12-31",
            rows=[_ticker_rows()[0]],
        ),
        _raw(
            tmp_path,
            family=subject.FAMILY_DEPTH,
            symbol="XCNUSDT",
            day="2021-01-01",
            rows=[_depth_rows()[0]],
            authority="accepted_v3_direct_recovery",
        ),
    ]
    gaps = [{"family": subject.FAMILY_TICKER, "symbol": "X", "kind": "cost_sample_unavailable"}]

    class Obj:
        def __init__(self, size: int, etag: str) -> None:
            self.size = size
            self.etag = etag

    items = [
        {
            "family": source.family,
            "symbol": source.native_symbol,
            "key": source.source_key,
            "object": Obj(source.byte_size, source.etag),
        }
        for source in sources
    ]
    expected = cost_manifest_digest(
        items,
        selector="first_midpoint_last_daily_book_v1",
        families=subject.FAMILIES,
        gaps=gaps,
    )
    monkeypatch.setattr(subject, "COST_MANIFEST_SHA256", expected)
    subject._manifest_reproof(sources, gaps)
    with pytest.raises(subject.CostCalibrationError, match="re-proved"):
        subject._manifest_reproof(sources[:-1], gaps)


def test_generation0_loader_authenticates_raw_and_sidecar_content_addresses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _raw(
        tmp_path,
        family=subject.FAMILY_DEPTH,
        symbol="XCNUSDT",
        day="2021-01-01",
        rows=[_depth_rows()[0]],
    )
    content_root = tmp_path / "content"
    raw_path = content_root / source.source_sha256[:2] / source.source_sha256
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(source.path.read_bytes())
    sidecar_body = (
        f"{source.source_sha256} {source.source_key.rsplit('/', 1)[-1]}\n".encode()
    )
    sidecar_sha = hashlib.sha256(sidecar_body).hexdigest()
    sidecar_path = content_root / sidecar_sha[:2] / sidecar_sha
    sidecar_path.parent.mkdir(parents=True)
    sidecar_path.write_bytes(sidecar_body)
    state = tmp_path / "state.sqlite3"
    connection = sqlite3.connect(state)
    connection.executescript(
        """
        CREATE TABLE plan_entry (
            provider TEXT, identity TEXT, payload_json TEXT,
            PRIMARY KEY(provider, identity)
        );
        CREATE TABLE completion (
            provider TEXT, identity TEXT, content_sha256 TEXT, content_path TEXT,
            listed_bytes INTEGER, retrieved_at TEXT, revision_json TEXT,
            validation_state TEXT,
            sidecar_sha256 TEXT, sidecar_path TEXT,
            PRIMARY KEY(provider, identity)
        );
        CREATE TABLE sidecar_fact (
            provider TEXT, identity TEXT, sidecar_sha256 TEXT, sidecar_path TEXT,
            provider_checksum TEXT, sidecar_bytes INTEGER,
            PRIMARY KEY(provider, identity)
        );
        """
    )
    connection.execute(f"PRAGMA application_id={subject.STATE_APPLICATION_ID}")
    connection.execute(f"PRAGMA user_version={subject.STATE_USER_VERSION}")
    payload = {
        "payload": {
            "key": source.source_key,
            "family": source.family,
            "symbol": source.native_symbol,
            "economic_interval": source.economic_day,
            "listed_bytes": source.byte_size,
            "etag": source.etag,
        }
    }
    connection.execute(
        "INSERT INTO plan_entry VALUES (?,?,?)",
        ("binance_vision", source.source_key, json.dumps(payload)),
    )
    connection.execute(
        "INSERT INTO completion VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            "binance_vision",
            source.source_key,
            source.source_sha256,
            str(raw_path),
            source.byte_size,
            "2026-08-31T00:00:00+00:00",
            '{"retained":true}',
            subject.OUTCOME_CHECKSUM_VERIFIED,
            sidecar_sha,
            str(sidecar_path),
        ),
    )
    connection.execute(
        "INSERT INTO sidecar_fact VALUES (?,?,?,?,?,?)",
        (
            "binance_vision",
            source.source_key,
            sidecar_sha,
            str(sidecar_path),
            source.source_sha256,
            len(sidecar_body),
        ),
    )
    connection.commit()
    connection.close()

    for name in (
        "authenticate_schema",
        "authenticate_domains",
        "authenticate_singletons",
        "authenticate_prefix",
        "_require_runnable_head",
    ):
        monkeypatch.setattr(subject.AcquisitionState, name, lambda _self: None)
    monkeypatch.setattr(
        subject.AcquisitionState,
        "seal_head_row",
        lambda _self: {"receipt_sha256": subject.GENERATION0_SEAL},
    )
    monkeypatch.setattr(subject, "ACCEPTED_GENERATION0_BINANCE_COMPLETIONS", 1)
    monkeypatch.setattr(subject, "ACCEPTED_GENERATION0_OBJECTS", 1)
    loaded = subject.load_generation0_cost_sources(
        state, content_root, {source.source_key}
    )
    assert loaded == (
        replace(
            source,
            path=raw_path,
            retrieval_time="2026-08-31T00:00:00+00:00",
            revision={"retained": True},
        ),
    )
    sidecar_path.write_bytes(b"changed")
    with pytest.raises(subject.CostCalibrationError, match="authority bytes changed"):
        subject.load_generation0_cost_sources(state, content_root, {source.source_key})


def test_recovery_manifest_selects_disjoint_book_ticker_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _raw(
        tmp_path,
        family=subject.FAMILY_TICKER,
        symbol="SNTUSDT",
        day="2024-03-30",
        rows=[_ticker_rows()[0]],
        authority="accepted_v3_direct_recovery",
    )
    recovery = tmp_path / "recovery"
    path = recovery.joinpath(*PurePosixPath(source.source_key).parts)
    path.parent.mkdir(parents=True)
    path.write_bytes(source.path.read_bytes())
    records = [
        {
            "record_type": "row",
            "record": {
                "family": subject.FAMILY_TICKER,
                "identity": source.source_key,
                "provider_checksum": source.source_sha256,
                "current_listed_bytes": source.byte_size,
                "current_listing": {"etag": source.etag},
            },
        }
    ]
    body = gzip.compress(b"".join(subject._canonical_json(row) for row in records), mtime=0)
    manifest = tmp_path / (hashlib.sha256(body).hexdigest() + ".json.gz")
    manifest.write_bytes(body)
    monkeypatch.setattr(subject, "V3_MANIFEST_SHA256", hashlib.sha256(body).hexdigest())
    monkeypatch.setattr(subject, "ACCEPTED_V3_ROWS", 1)
    monkeypatch.setattr(subject, "ACCEPTED_V3_BYTES", source.byte_size)
    monkeypatch.setattr(subject, "ACCEPTED_V3_METRICS_ROWS", 0)
    monkeypatch.setattr(subject, "ACCEPTED_RECOVERY_OBJECTS", 1)
    monkeypatch.setattr(subject, "ACCEPTED_RECOVERY_BYTES", source.byte_size)
    loaded = subject.load_recovery_cost_sources(manifest, recovery, {source.source_key})
    assert len(loaded) == 1 and loaded[0].retrieval_time is None


def test_report_manifest_retains_family_scoped_source_gaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = "data/futures/um/daily/bookTicker/BTCUSDT/BTCUSDT-bookTicker-2020-01-01.zip"
    gap = {
        "blocking": True,
        "family": subject.FAMILY_DEPTH,
        "family_group": "bookDepth",
        "kind": "cost_sample_unavailable",
        "status": "cost_sample_unavailable",
        "symbol": "MISSING",
    }
    report = {
        "storage": {
            "cost_sample": {
                "keys": [key],
                "gaps": [gap],
                "object_count": 1,
                "compressed_raw_bytes": 10,
                "families": list(subject.FAMILIES),
                "selector": "first_midpoint_last_daily_book_v1",
                "manifest_digest_version": subject.COST_MANIFEST_DIGEST_VERSION,
                "manifest_digest": "a" * 64,
            }
        }
    }
    monkeypatch.setattr(subject, "ACCEPTED_COST_OBJECTS", 1)
    monkeypatch.setattr(subject, "ACCEPTED_COST_BYTES", 10)
    monkeypatch.setattr(subject, "ACCEPTED_SOURCE_GAPS", 1)
    monkeypatch.setattr(subject, "COST_MANIFEST_SHA256", "a" * 64)
    keys, gaps = subject._report_manifest(report)
    assert keys == {key} and gaps == (gap,)


def test_sizing_validation_binds_each_component_allocation() -> None:
    sizing = {
        "typed_schema_contract": {
            "cost_component_schemas": subject.product_schema_contract(subject.PRODUCT)
        },
        "projections": {"row_batch_cap": subject.SIZING_ROW_BATCH},
        "cost_calibration_components": {
            component: {
                "component": component,
                "projected_rows": limits["rows"],
                "projected_bytes": limits["bytes"],
                "largest_partition_bytes": limits["largest_partition_bytes"],
                "partition_count": limits["partitions"],
            }
            for component, limits in subject.COMPONENT_LIMITS.items()
        },
    }
    subject._validate_sizing(sizing)
    sizing["cost_calibration_components"][subject.COMPONENT_TICKER][
        "largest_partition_bytes"
    ] -= 1
    with pytest.raises(subject.CostCalibrationError, match="allocation changed"):
        subject._validate_sizing(sizing)


def test_fee_gap_fixture_scales_to_771_distinct_memberships() -> None:
    memberships = [_identity(f"S{index}USDT") for index in range(771)]
    rows = [
        {
            **identity.row(),
            "required_product": subject.PRODUCT,
            "gap_kind": subject.FEE_GAP_KIND,
            "gap_status": subject.FEE_GAP_KIND,
            "blocking": False,
            "authority_class": subject.FEE_AUTHORITY_CLASS,
            "explained_by": "no_free_reproducible_historical_fee_authority",
        }
        for identity in memberships
    ]
    table = pa.Table.from_pylist(rows, schema=subject.SCHEMAS[subject.COMPONENT_FEE_GAP])
    assert table.num_rows == 771
    assert len(set(table.column("native_symbol").to_pylist())) == 771


def test_scenario_rows_are_exact_nonbackdated_configuration() -> None:
    rows = list(fee_scenario_rows())
    assert [row["maker_rate"] for row in rows] == [Decimal("0.0005"), Decimal("0.0010")]
    assert [row["taker_rate"] for row in rows] == [Decimal("0.0005"), Decimal("0.0010")]
    assert {row["policy_known_at"] for row in rows} == {"2026-08-23T03:00:00Z"}
    for row in rows:
        assert row["charges_each_side"] is True
        assert row["maker_credit_enabled"] is False
        assert row["rebates_enabled"] is False
        assert row["vip_discounts_enabled"] is False
        assert row["referral_discounts_enabled"] is False
        assert row["bnb_discount_enabled"] is False
