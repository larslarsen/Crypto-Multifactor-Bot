from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import cryptofactors.ingest.binance_usdm_cost_calibration as producer
import cryptofactors.ingest.binance_usdm_cost_finalization as subject
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    PARQUET_COMPRESSION,
    PARQUET_COMPRESSION_LEVEL,
    PARQUET_VERSION,
)


@dataclass(frozen=True)
class Fixture:
    root: Path
    sources: tuple[producer.RawCostObject, ...]
    memberships: tuple[producer.MembershipIdentity, ...]
    gaps: tuple[dict[str, Any], ...]


def _zip(member: str, rows: list[list[str]], header: list[str] | None = None) -> bytes:
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
    family: str,
    symbol: str,
    day: str,
    rows: list[list[str]],
) -> producer.RawCostObject:
    kind = family.rsplit("/", 1)[1]
    basename = f"{symbol}-{kind}-{day}"
    fields = producer.KNOWN_ARCHIVE_SCHEMAS[kind]["headerless"]
    body = _zip(f"{basename}.csv", rows, list(fields))
    digest = hashlib.sha256(body).hexdigest()
    path = tmp_path / digest
    path.write_bytes(body)
    return producer.RawCostObject(
        source_key=f"data/futures/um/daily/{kind}/{symbol}/{basename}.zip",
        family=family,
        native_symbol=symbol,
        economic_day=day,
        path=path,
        source_sha256=digest,
        byte_size=len(body),
        etag="etag",
        authority="accepted_generation_0_completion",
        checksum_authority="binance_checksum_sidecar",
        retrieval_time="2026-08-31T00:00:00+00:00",
    )


def _identity(symbol: str) -> producer.MembershipIdentity:
    return producer.MembershipIdentity(
        "BINANCE_USDM",
        symbol,
        None,
        None,
        "reference_identity_not_yet_created",
    )


def _make_fixture(tmp_path: Path) -> Fixture:
    ticker_rows = [
        ["1", "100", "2", "101", "3", "1609459199999", "1609459199000"],
        ["2", "100", "1", "0E-8", "0", "1609459200000", "1609459200000"],
        ["3", "0", "0", "102", "0", "1609459200000", "1609459200000"],
        ["4", "0", "0", "0", "0", "1609459200000", "1609459200000"],
    ]
    depth_rows = [
        ["2021-01-01 00:00:00", "-5", "0", "0"],
        ["2021-01-01 00:00:00", "-4", "1", "2"],
        ["2021-01-01 00:00:00", "-3", "2", "3"],
    ]
    sources = (
        _raw(tmp_path, producer.FAMILY_TICKER, "BTCUSDT", "2020-12-31", ticker_rows),
        _raw(tmp_path, producer.FAMILY_DEPTH, "XCNUSDT", "2021-01-01", depth_rows),
    )
    memberships = (_identity("BTCUSDT"), _identity("XCNUSDT"))
    gaps = (
        {
            "blocking": True,
            "family": producer.FAMILY_TICKER,
            "family_group": "bookTicker",
            "kind": "cost_sample_unavailable",
            "status": "cost_sample_unavailable",
            "symbol": "XCNUSDT",
        },
    )
    root = tmp_path / ".cost"
    result = producer.normalize_cost_sources(sources, memberships, gaps, root)
    result.completion_path.unlink()
    result.completion_path.parent.rmdir()
    return Fixture(root, sources, memberships, gaps)


def _entries(root: Path) -> list[dict[str, Any]]:
    result = []
    for path in sorted((value for value in root.rglob("*") if value.is_file()), key=lambda value: value.relative_to(root).as_posix()):
        body = path.read_bytes()
        result.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
            }
        )
    return result


def _directories(root: Path) -> int:
    return sum(path.is_dir() for path in root.rglob("*"))


def _lineages(root: Path) -> list[dict[str, Any]]:
    return [json.loads(path.read_text()) for path in root.glob(".lineage/*/*/*/*.json")]


def _pin(monkeypatch: pytest.MonkeyPatch, fixture: Fixture) -> None:
    entries = _entries(fixture.root)
    gap_path = next(fixture.root.glob(".source-gaps/*.json"))
    gap_body = gap_path.read_bytes()
    lineages = _lineages(fixture.root)
    components: dict[str, dict[str, int]] = {}
    for component in producer.COST_COMPONENTS:
        selected = [value for value in lineages if value["component"] == component]
        components[component] = {
            "partitions": len(selected),
            "rows": sum(value["row_count"] for value in selected),
            "parquet_bytes": sum(value["parquet_bytes"] for value in selected),
            "largest_partition_bytes": max(value["parquet_bytes"] for value in selected),
        }
    source_rows = {
        source.source_key: (4 if source.family == producer.FAMILY_TICKER else 3)
        for source in fixture.sources
    }
    compact = [
        {"source_key": key, "physical_rows": source_rows[key]}
        for key in sorted(source_rows)
    ]
    digest = hashlib.sha256(subject._canonical_json(entries, newline=False)).hexdigest()
    monkeypatch.setattr(subject, "PRESERVED_INVENTORY_SHA256", digest)
    monkeypatch.setattr(subject, "PRESERVED_FILES", len(entries))
    monkeypatch.setattr(subject, "PRESERVED_DIRECTORIES", _directories(fixture.root))
    monkeypatch.setattr(subject, "PRESERVED_BYTES", sum(value["bytes"] for value in entries))
    monkeypatch.setattr(subject, "SOURCE_GAP_SHA256", hashlib.sha256(gap_body).hexdigest())
    monkeypatch.setattr(subject, "SOURCE_GAP_BYTES", len(gap_body))
    monkeypatch.setattr(subject, "SOURCE_ROW_FACTS_SHA256", hashlib.sha256(subject._canonical_json(compact, newline=False)).hexdigest())
    monkeypatch.setattr(subject, "EXPECTED_SOURCE_OBJECTS", 2)
    monkeypatch.setattr(subject, "EXPECTED_SOURCE_BYTES", sum(value.byte_size for value in fixture.sources))
    monkeypatch.setattr(subject, "EXPECTED_GENERATION0_OBJECTS", 2)
    monkeypatch.setattr(subject, "EXPECTED_RECOVERY_OBJECTS", 0)
    monkeypatch.setattr(subject, "EXPECTED_TICKER_OBJECTS", 1)
    monkeypatch.setattr(subject, "EXPECTED_DEPTH_OBJECTS", 1)
    monkeypatch.setattr(subject, "EXPECTED_MEMBERSHIPS", 2)
    monkeypatch.setattr(subject, "EXPECTED_SOURCE_GAPS", 1)
    monkeypatch.setattr(subject, "EXPECTED_BOOK_ROWS", 7)
    monkeypatch.setattr(
        subject,
        "EXPECTED_ALL_ROWS",
        sum(value["rows"] for value in components.values()),
    )
    monkeypatch.setattr(subject, "EXPECTED_QUOTE_STATES", {"two_sided": 1, "bid_only": 1, "ask_only": 1, "empty": 1})
    monkeypatch.setattr(subject, "EXPECTED_COMPONENTS", components)


def _finalize(fixture: Fixture, **kwargs: Any) -> subject.CostFinalizationResult:
    return subject._finalize_verified_artifacts(
        sources=fixture.sources,
        memberships=fixture.memberships,
        gaps=fixture.gaps,
        output_root=fixture.root,
        **kwargs,
    )


def _replace_partition(
    fixture: Fixture,
    component: str,
    change: Any,
    *,
    row_group_size: int | None = None,
) -> None:
    lineage_path = max(
        fixture.root.glob(f".lineage/{component}/*/*/*.json"),
        key=lambda path: json.loads(path.read_text())["row_count"],
    )
    lineage = json.loads(lineage_path.read_text())
    parquet_path = fixture.root / lineage["parquet_path"]
    table = change(pq.read_table(parquet_path))
    temporary = fixture.root / ".staging" / "fixture.parquet"
    pq.write_table(
        table,
        temporary,
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
        version=PARQUET_VERSION,
        write_statistics=False,
        store_schema=True,
        row_group_size=row_group_size,
    )
    body = temporary.read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    replacement = parquet_path.with_name(f"{digest}.parquet")
    parquet_path.unlink()
    temporary.rename(replacement)
    lineage["parquet_path"] = replacement.relative_to(fixture.root).as_posix()
    lineage["parquet_sha256"] = digest
    lineage["parquet_bytes"] = len(body)
    lineage["row_count"] = table.num_rows
    lineage_body = producer._canonical_json(lineage)
    lineage_replacement = lineage_path.with_name(f"{hashlib.sha256(lineage_body).hexdigest()}.json")
    lineage_path.unlink()
    lineage_replacement.write_bytes(lineage_body)


def _set_value(table: pa.Table, name: str, index: int, value: Any) -> pa.Table:
    values = table.column(name).to_pylist()
    values[index] = value
    field_index = table.schema.get_field_index(name)
    return table.set_column(field_index, table.schema.field(field_index), pa.array(values, type=table.schema.field(field_index).type))


def test_exact_reviewed_artifacts_publish_completion_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)
    before_entries = _entries(fixture.root)
    before = {value["path"] for value in before_entries}
    before_stats = {
        value["path"]: (
            (fixture.root / value["path"]).stat().st_ino,
            (fixture.root / value["path"]).stat().st_mtime_ns,
            value["sha256"],
        )
        for value in before_entries
    }
    result = _finalize(fixture)
    after = {value["path"] for value in _entries(fixture.root)}
    assert after - before == {result.completion_path.relative_to(fixture.root).as_posix()}
    assert before_stats == {
        path: (
            (fixture.root / path).stat().st_ino,
            (fixture.root / path).stat().st_mtime_ns,
            hashlib.sha256((fixture.root / path).read_bytes()).hexdigest(),
        )
        for path in before
    }
    document = json.loads(result.completion_path.read_text())
    assert document["normalizer_source_sha256"] == subject.ORIGINAL_PRODUCER_SHA256
    assert document["normalizer_integration_commit"] == subject.ORIGINAL_INTEGRATION_COMMIT
    assert document["finalizer_source_sha256"] == hashlib.sha256(Path(subject.__file__).read_bytes()).hexdigest()
    assert document["encoded_validation_scope"]["independent_complete_csv_to_parquet_value_equality_claimed"] is False


def test_exact_only_ticker_projection_variance_is_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)
    limits = {key: dict(value) for key, value in producer.COMPONENT_LIMITS.items()}
    limits[producer.COMPONENT_TICKER]["rows"] = 3
    monkeypatch.setattr(producer, "COMPONENT_LIMITS", limits)
    result = _finalize(fixture)
    disposition = json.loads(result.completion_path.read_text())["ticker_row_projection_disposition"]
    assert disposition == {
        "projected_rows": 3,
        "actual_rows": 4,
        "excess_rows": 1,
        "status": "EXCEEDED_REVIEWED_EXACT_ARTIFACT_VARIANCE",
        "ordinary_sizing_check_passed": False,
    }


def test_unreviewed_ticker_row_variance_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)
    changed = {key: dict(value) for key, value in subject.EXPECTED_COMPONENTS.items()}
    changed[producer.COMPONENT_TICKER]["rows"] += 1
    monkeypatch.setattr(subject, "EXPECTED_COMPONENTS", changed)
    with pytest.raises(subject.Error, match="reviewed component facts"):
        _finalize(fixture)


@pytest.mark.parametrize("mutation", ["missing", "corrupt", "foreign", "symlink"])
def test_inventory_mutations_refuse_without_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)
    target = next(fixture.root.glob(".partitions/*/*/*/*.parquet"))
    if mutation == "missing":
        target.unlink()
    elif mutation == "corrupt":
        target.write_bytes(b"changed")
    elif mutation == "foreign":
        (fixture.root / "foreign.json").write_text("{}")
    else:
        outside = tmp_path / "outside"
        outside.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(outside)
    with pytest.raises(subject.Error):
        _finalize(fixture)
    assert not list(fixture.root.glob(".complete/*.json"))


def test_absent_or_symlink_root_refuses(tmp_path: Path) -> None:
    source_root = tmp_path / "missing"
    with pytest.raises(subject.Error, match="absent"):
        subject._finalize_verified_artifacts(sources=(), memberships=(), gaps=(), output_root=source_root)
    target = tmp_path / ".target"
    target.mkdir()
    linked = tmp_path / ".linked"
    linked.symlink_to(target)
    with pytest.raises(subject.Error, match="symlink"):
        subject._finalize_verified_artifacts(sources=(), memberships=(), gaps=(), output_root=linked)


def test_missing_preserved_staging_directory_refuses_without_recreation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)
    staging = fixture.root / ".staging"
    staging.rmdir()
    with pytest.raises(subject.Error, match="staging directory"):
        _finalize(fixture)
    assert not staging.exists()


def test_raw_authority_hash_mismatch_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)
    fixture.sources[0].path.write_bytes(b"changed")
    with pytest.raises(subject.Error, match="authority bytes changed"):
        _finalize(fixture)


def test_pinned_report_authority_mismatch_refuses_before_output(
    tmp_path: Path,
) -> None:
    report = tmp_path / "report.json"
    report.write_text("{}")
    with pytest.raises(subject.Error, match="authority bytes changed"):
        subject.finalize_from_authorities(
            report_path=report,
            sizing_path=tmp_path / "sizing.json",
            generation0_state=tmp_path / "state.sqlite",
            generation0_content_root=tmp_path / "content",
            v3_manifest=tmp_path / "manifest.json.gz",
            recovery_root=tmp_path / "recovery",
            membership_root=tmp_path / "membership",
            output_root=tmp_path / ".cost",
        )


def test_producer_identity_mismatch_refuses_before_output_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)
    monkeypatch.setattr(subject, "ORIGINAL_PRODUCER_SHA256", "0" * 64)
    with pytest.raises(subject.Error, match="producer module identity"):
        _finalize(fixture)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("source_row_ordinal", 9, "ordinal"),
        ("transaction_time", 1609459200001, "source-day"),
        ("venue_symbol", "ETHUSDT", "membership"),
        ("best_ask_price", Decimal("99"), "crossed"),
    ],
)
def test_ticker_encoded_semantic_mutations_refuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    column: str,
    value: Any,
    message: str,
) -> None:
    fixture = _make_fixture(tmp_path)
    _replace_partition(
        fixture,
        producer.COMPONENT_TICKER,
        lambda table: _set_value(table, column, 0, value),
    )
    _pin(monkeypatch, fixture)
    with pytest.raises(subject.Error, match=message):
        _finalize(fixture)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("percentage", Decimal("0"), "band"),
        ("depth", Decimal("-1"), "depth value"),
        ("timestamp", 1609545600001, "source-day"),
    ],
)
def test_depth_encoded_semantic_mutations_refuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    column: str,
    value: Any,
    message: str,
) -> None:
    fixture = _make_fixture(tmp_path)
    _replace_partition(
        fixture,
        producer.COMPONENT_DEPTH,
        lambda table: _set_value(table, column, 0, value),
    )
    _pin(monkeypatch, fixture)
    with pytest.raises(subject.Error, match=message):
        _finalize(fixture)


def test_row_group_cap_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = _make_fixture(tmp_path)
    _replace_partition(fixture, producer.COMPONENT_TICKER, lambda table: table, row_group_size=4)
    _pin(monkeypatch, fixture)
    monkeypatch.setattr(subject, "SIZING_ROW_BATCH", 2)
    with pytest.raises(subject.Error, match="row-group cap"):
        _finalize(fixture)


def test_encoded_row_count_and_declared_ordinal_domain_must_reconcile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _replace_partition(
        fixture,
        producer.COMPONENT_TICKER,
        lambda table: table.slice(0, table.num_rows - 1),
    )
    _pin(monkeypatch, fixture)
    with pytest.raises(subject.Error, match="ordinal range"):
        _finalize(fixture)


def test_fee_gap_semantics_refuse_zero_cost_inference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _replace_partition(
        fixture,
        producer.COMPONENT_FEE_GAP,
        lambda table: _set_value(table, "explained_by", 0, "missing_means_zero"),
    )
    _pin(monkeypatch, fixture)
    with pytest.raises(subject.Error, match="fee gap semantics"):
        _finalize(fixture)


def test_scenario_policy_cannot_be_backdated_or_reclassified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _replace_partition(
        fixture,
        producer.COMPONENT_SCENARIO,
        lambda table: _set_value(table, "policy_known_at", 0, "2020-01-01T00:00:00Z"),
    )
    _pin(monkeypatch, fixture)
    limits = {key: dict(value) for key, value in producer.COMPONENT_LIMITS.items()}
    measured = subject.EXPECTED_COMPONENTS[producer.COMPONENT_SCENARIO]
    limits[producer.COMPONENT_SCENARIO]["bytes"] = measured["parquet_bytes"]
    limits[producer.COMPONENT_SCENARIO]["largest_partition_bytes"] = measured[
        "largest_partition_bytes"
    ]
    monkeypatch.setattr(producer, "COMPONENT_LIMITS", limits)
    with pytest.raises(subject.Error, match="scenario policy"):
        _finalize(fixture)


def test_completion_bytes_are_inside_immutable_total_allocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)
    monkeypatch.setattr(producer, "NORMALIZED_ALLOCATION_BYTES", subject.PRESERVED_BYTES)
    with pytest.raises(subject.Error, match="including completion"):
        _finalize(fixture)
    assert not list(fixture.root.glob(".complete/*.json"))


def test_interruption_leaves_only_empty_complete_directory_and_retry_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)

    def interrupt(_stage: Path, _destination: Path) -> None:
        raise RuntimeError("interrupt")

    with pytest.raises(RuntimeError, match="interrupt"):
        _finalize(fixture, hooks=subject.FinalizationHooks(before_completion_publish=interrupt))
    assert (fixture.root / ".complete").is_dir()
    assert not list((fixture.root / ".complete").iterdir())
    result = _finalize(fixture)
    assert result.completion_path.is_file()


def test_replay_is_byte_identical_and_no_clobber(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)
    first = _finalize(fixture)
    first_body = first.completion_path.read_bytes()
    second = _finalize(fixture)
    assert second.completion_reused is True
    assert second.completion_sha256 == first.completion_sha256
    assert second.completion_path.read_bytes() == first_body
    assert len(list((fixture.root / ".complete").iterdir())) == 1
    assert not list((fixture.root / ".staging").iterdir())


def test_foreign_or_corrupt_completion_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)
    result = _finalize(fixture)
    result.completion_path.write_bytes(b"changed")
    with pytest.raises(subject.Error):
        _finalize(fixture)


def test_csv_parser_and_parquet_writer_are_never_invoked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("forbidden conversion path")

    monkeypatch.setattr(producer, "_member", forbidden)
    monkeypatch.setattr(pq, "write_table", forbidden)
    monkeypatch.setattr(pq, "ParquetWriter", forbidden)
    result = _finalize(fixture)
    assert result.source_rows == 7


def test_source_gap_hash_and_exact_facts_are_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _make_fixture(tmp_path)
    _pin(monkeypatch, fixture)
    monkeypatch.setattr(subject, "SOURCE_GAP_SHA256", "0" * 64)
    with pytest.raises(subject.Error, match="source-gap"):
        _finalize(fixture)


def test_cli_exposes_only_authority_and_output_paths() -> None:
    source = Path("scripts/research/finalize_binance_usdm_cost_calibration.py").read_text()
    assert "--inventory" not in source
    assert "--row-override" not in source
    assert "normalize_from_authorities" not in source
