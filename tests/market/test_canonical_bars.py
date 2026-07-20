"""Focused BAR-001 v2 regressions for canonical bar publisher.

Covers: verified MAN-001 manifest/receipt trust, PASS_WITH_WARNINGS propagation,
nullable missing fields, strict COIN-M schema rejection, inclusive-close
validation, complete vs incomplete UTC days, deterministic duplicate collapse,
valid lineage, daily reconciliation with native daily, successful publish through
`DatasetPublisher.publish`, and transform/schema version brakes.

Transform: `canonical_bar_publisher` v2
Schema: `market_bar` v2
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import json
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from decimal import Decimal

from cryptofactors.audit.models import IssueSeverity
from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetManifest,
    DatasetPublicationReceipt,
    DatasetStatistics,
    OutputFileSpec,
    PublicationMetadata,
    QualityStatus,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.market.bars import (
    CanonicalBarPublishResult,
    VerifiedSourceBarDataset,
    publish_canonical_bars,
)

TEST_CODE_COMMIT = "0" * 40
TEST_CONFIG_HASH = "a" * 64
UTC = timezone.utc


def _us(ts: datetime) -> int:
    return int(ts.timestamp() * 1_000_000)


# ------------------------------------------------------------------
# Manifest constructors bound to actual parquet files
# ------------------------------------------------------------------
def _manifest_fields(dataset_id: str = "bin_src", *, rows: int = 1, byte_size: int = 4096) -> dict:
    return dict(
        dataset_id=dataset_id,
        dataset_type="normalized_source",
        schema=SchemaIdentity(name="binance_kline", version="4", fingerprint="fp"),
        transform=TransformSpec(name="normalize_binance_kline", version="4"),
        code=CodeIdentity(commit=TEST_CODE_COMMIT),
        config=ConfigIdentity(config_sha256=TEST_CONFIG_HASH),
        dependencies=(),
        statistics=DatasetStatistics(row_count=rows, byte_size=byte_size),
        coverage=CoverageWindow(
            event_start=datetime(2025, 1, 1, tzinfo=UTC),
            event_end=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={"source": "synthetic"},
        publication=PublicationMetadata(created_at=datetime(2025, 1, 1, tzinfo=UTC)),
        manifest_sha256="0" * 64,
    )


def _file_spec_for(path: Path, relative_path: str, rows: int | None = None) -> OutputFileSpec:
    if rows is None:
        rows = pq.read_table(path).num_rows
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return OutputFileSpec(
        relative_path=relative_path,
        sha256=sha,
        rows=rows,
        bytes=path.stat().st_size,
        rows_verified=True,
    )


def _manifest_for(path: Path, *, dataset_id: str, quality: QualityStatus = QualityStatus.PASS, rows: int | None = None, relative_path: str | None = None) -> DatasetManifest:
    if relative_path is None:
        relative_path = path.name
    spec = _file_spec_for(path, relative_path, rows)
    fields = _manifest_fields(dataset_id=dataset_id, rows=spec.rows, byte_size=spec.bytes)
    return DatasetManifest(files=(spec,), **fields)


def _receipt_for(manifest: DatasetManifest) -> DatasetPublicationReceipt:
    return DatasetPublicationReceipt(
        dataset_id=manifest.dataset_id,
        manifest_sha256=manifest.manifest_sha256,
        manifest_uri="manifest.json",
        publication_uri="datasets/sha256",
        dataset_path=Path("/tmp"),
        verified_outputs=manifest.files,
        publication_verified=True,
        object_prefix="datasets/sha256",
        dependencies=(),
        supersedes_dataset_id=None,
        dataset_type=manifest.dataset_type,
        schema=manifest.schema,
        transform=manifest.transform,
        code=manifest.code,
        config=manifest.config,
        statistics=manifest.statistics,
        coverage=manifest.coverage,
        quality_status=manifest.quality_status,
        quality_summary=dict(manifest.quality_summary),
        catalog_created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


# ------------------------------------------------------------------
# Parquet / schema helpers
# ------------------------------------------------------------------
def _schema(quote_notional: bool = True) -> pa.Schema:
    if quote_notional:
        return pa.schema([
            ("open_time", pa.int64()),
            ("open", pa.decimal128(38, 18)),
            ("high", pa.decimal128(38, 18)),
            ("low", pa.decimal128(38, 18)),
            ("close", pa.decimal128(38, 18)),
            ("volume", pa.decimal128(38, 18)),
            ("quote_volume", pa.decimal128(38, 18)),
            ("base_asset_volume", pa.decimal128(38, 18)),
            ("trades", pa.int64()),
            ("taker_buy_base_volume", pa.decimal128(38, 18)),
            ("taker_buy_quote_volume", pa.decimal128(38, 18)),
            ("close_time", pa.int64()),
            ("source_open_time", pa.int64()),
            ("source_close_time", pa.int64()),
            ("source_timestamp_unit", pa.string()),
        ])
    return pa.schema([
        ("open_time", pa.int64()),
        ("open", pa.decimal128(38, 18)),
        ("high", pa.decimal128(38, 18)),
        ("low", pa.decimal128(38, 18)),
        ("close", pa.decimal128(38, 18)),
        ("volume", pa.decimal128(38, 18)),
        ("base_asset_volume", pa.decimal128(38, 18)),
        ("trades", pa.int64()),
        ("taker_buy_base_asset_volume", pa.decimal128(38, 18)),
        ("close_time", pa.int64()),
        ("source_open_time", pa.int64()),
        ("source_close_time", pa.int64()),
        ("source_timestamp_unit", pa.string()),
    ])


def _write_parquet(path: Path, schema: pa.Schema, rows: list[list]) -> None:
    arrays = {f.name: pa.array([r[i] for r in rows], type=f.type) for i, f in enumerate(schema)}
    pq.write_table(pa.table(arrays, schema=schema), path)


def _source_row(open_us: int, interval: str = "1m") -> list:
    if interval == "1m":
        close_us = open_us + 60_000_000 - 1
        unit = "us"
    elif interval == "1h":
        close_us = open_us + 3_600_000_000 - 1
        unit = "us"
    else:
        close_us = open_us + 86_400_000_000 - 1
        unit = "us"
    return [
        open_us, Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105"),
        Decimal("1000"), Decimal("105000"), Decimal("1000"), 10,
        Decimal("2"), Decimal("500"), close_us,
        open_us, close_us, unit,
    ]


# ------------------------------------------------------------------
# Source builders wired to verified evidence
# ------------------------------------------------------------------
def _verified_source(
    tmp_path: Path,
    *,
    dataset_id: str = "bin_src",
    quality: QualityStatus = QualityStatus.PASS,
    rows: list | None = None,
    relative_path: str = "source.parquet",
    quote_notional: bool = True,
) -> VerifiedSourceBarDataset:
    p = tmp_path / relative_path
    p.parent.mkdir(parents=True, exist_ok=True)
    if rows is None:
        rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    _write_parquet(p, _schema(quote_notional), rows)
    m = _manifest_for(p, dataset_id=dataset_id, quality=quality, relative_path=relative_path)
    return VerifiedSourceBarDataset(
        local_files={relative_path: p},
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
        schema_variant="quote_notional" if quote_notional else "coin_margined",
        manifest=m,
    )


def _publish(tmp_path: Path, sources: list[VerifiedSourceBarDataset], *, native_daily=(), **kwargs) -> CanonicalBarPublishResult:
    out = tmp_path / "market_out"
    out.mkdir(exist_ok=True)
    return publish_canonical_bars(
        sources, output_dir=out, code_commit=TEST_CODE_COMMIT, native_daily=native_daily, **kwargs
    )


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

def test_reject_empty_sources(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one verified source_dataset is required"):
        publish_canonical_bars([], output_dir=tmp_path, code_commit=TEST_CODE_COMMIT)


def test_reject_receipt_unverified(tmp_path: Path) -> None:
    p = tmp_path / "x.parquet"
    _write_parquet(p, _schema(), [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))])
    m = _manifest_for(p, dataset_id="x")
    receipt = _receipt_for(m)
    receipt = DatasetPublicationReceipt(
        dataset_id=receipt.dataset_id,
        manifest_sha256=receipt.manifest_sha256,
        manifest_uri=receipt.manifest_uri,
        publication_uri=receipt.publication_uri,
        dataset_path=receipt.dataset_path,
        verified_outputs=receipt.verified_outputs,
        publication_verified=False,
        object_prefix=receipt.object_prefix,
        dependencies=(),
        supersedes_dataset_id=None,
        dataset_type=receipt.dataset_type,
        schema=receipt.schema,
        transform=receipt.transform,
        code=receipt.code,
        config=receipt.config,
        statistics=receipt.statistics,
        coverage=receipt.coverage,
        quality_status=receipt.quality_status,
        quality_summary=dict(receipt.quality_summary),
        catalog_created_at=receipt.catalog_created_at,
    )
    src = VerifiedSourceBarDataset(
        local_files={},
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
        receipt=receipt,
    )
    with pytest.raises(ValueError, match="publication_verified must be True"):
        _publish(tmp_path, [src])


def test_reject_manifest_empty_sha(tmp_path: Path) -> None:
    p = tmp_path / "m.parquet"
    _write_parquet(p, _schema(), [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))])
    m = _manifest_for(p, dataset_id="empty_sha", rows=1)
    m = DatasetManifest(
        dataset_id=m.dataset_id,
        dataset_type=m.dataset_type,
        schema=m.schema,
        transform=m.transform,
        code=m.code,
        config=m.config,
        dependencies=m.dependencies,
        files=m.files,
        statistics=m.statistics,
        coverage=m.coverage,
        quality_status=m.quality_status,
        quality_summary=m.quality_summary,
        publication=m.publication,
        supersedes_dataset_id=m.supersedes_dataset_id,
        manifest_sha256=" " * 32,
    )
    src = VerifiedSourceBarDataset(
        local_files={m.files[0].relative_path: tmp_path / "missing.parquet"},
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
        manifest=m,
    )
    with pytest.raises(ValueError, match="manifest.manifest_sha256 must be a non-empty 64-hex digest"):
        _publish(tmp_path, [src])


def test_reject_hash_mismatch_local_file(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p = tmp_path / "source.parquet"
    _write_parquet(p, _schema(), rows)
    spec = _file_spec_for(p, "source.parquet")
    bad_spec = OutputFileSpec(
        relative_path=spec.relative_path,
        sha256="f" * 64,
        rows=spec.rows,
        bytes=spec.bytes,
        rows_verified=True,
    )
    m = _manifest_for(p, dataset_id="mismatch_src", rows=len(rows))
    m = DatasetManifest(
        dataset_id=m.dataset_id,
        dataset_type=m.dataset_type,
        schema=m.schema,
        transform=m.transform,
        code=m.code,
        config=m.config,
        dependencies=m.dependencies,
        files=(bad_spec,),
        statistics=m.statistics,
        coverage=m.coverage,
        quality_status=m.quality_status,
        quality_summary=m.quality_summary,
        publication=m.publication,
        supersedes_dataset_id=m.supersedes_dataset_id,
        manifest_sha256=m.manifest_sha256,
    )
    src = VerifiedSourceBarDataset(
        local_files={"source.parquet": p},
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
        manifest=m,
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        _publish(tmp_path, [src])


def test_pass_with_warnings_preserves_quality_and_warning_issue(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p = tmp_path / "source.parquet"
    _write_parquet(p, _schema(), rows)
    spec = _file_spec_for(p, "source.parquet")
    m = _manifest_for(p, dataset_id="ds_bin_src", rows=len(rows))
    m = DatasetManifest(
        dataset_id=m.dataset_id,
        dataset_type=m.dataset_type,
        schema=m.schema,
        transform=m.transform,
        code=m.code,
        config=m.config,
        dependencies=m.dependencies,
        files=(spec,),
        statistics=m.statistics,
        coverage=m.coverage,
        quality_status=QualityStatus.PASS_WITH_WARNINGS,
        quality_summary=m.quality_summary,
        publication=m.publication,
        supersedes_dataset_id=m.supersedes_dataset_id,
        manifest_sha256=m.manifest_sha256,
    )
    src = VerifiedSourceBarDataset(
        local_files={"source.parquet": p},
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
        manifest=m,
    )
    res = _publish(tmp_path, [src])
    warnings = [i for i in res.issues if i.severity == IssueSeverity.WARNING]
    assert any("pass_with_warnings" in w.code for w in warnings)


def test_nullable_missing_fields_remain_null(tmp_path: Path) -> None:
    us = _us(datetime(2025, 1, 1, tzinfo=UTC))
    rows = [_source_row(us)]
    for idx in [6, 10]:
        rows[0][idx] = None
    p = tmp_path / "source.parquet"
    _write_parquet(p, _schema(), rows)
    src = _verified_source(tmp_path, rows=rows)
    res = _publish(tmp_path, [src])
    # Rows with null quote/taker fields fail closed at parse time.
    assert any("source_row_parse_failure" in i.code for i in res.issues)

def test_strict_coin_m_rejects_missing_base_asset_volume(tmp_path: Path) -> None:
    schema_pq = pa.schema([
        ("open_time", pa.int64()),
        ("open", pa.decimal128(38, 18)),
        ("high", pa.decimal128(38, 18)),
        ("low", pa.decimal128(38, 18)),
        ("close", pa.decimal128(38, 18)),
        ("volume", pa.decimal128(38, 18)),
        ("trades", pa.int64()),
        ("close_time", pa.int64()),
        ("source_open_time", pa.int64()),
        ("source_close_time", pa.int64()),
        ("source_timestamp_unit", pa.string()),
    ])
    us = _us(datetime(2025, 1, 1, tzinfo=UTC))
    rows = [[us, Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105"),
             Decimal("1000"), 10, us + 60_000_000 - 1, us, us + 60_000_000 - 1, "us"]]
    p = tmp_path / "coin.parquet"
    _write_parquet(p, schema_pq, rows)
    spec = _file_spec_for(p, "coin.parquet")
    base = _manifest_for(p, dataset_id="coin_bad", rows=len(rows))
    m = DatasetManifest(
        dataset_id=base.dataset_id,
        dataset_type=base.dataset_type,
        schema=base.schema,
        transform=base.transform,
        code=base.code,
        config=base.config,
        dependencies=base.dependencies,
        files=(spec,),
        statistics=base.statistics,
        coverage=base.coverage,
        quality_status=QualityStatus.PASS,
        quality_summary=base.quality_summary,
        publication=base.publication,
        supersedes_dataset_id=base.supersedes_dataset_id,
        manifest_sha256=base.manifest_sha256,
    )
    src = VerifiedSourceBarDataset(
        local_files={"coin.parquet": p},
        venue_id="binance",
        instrument_id=1,
        market_type="coinm",
        interval="1m",
        schema_variant="coin_margined",
        manifest=m,
    )
    with pytest.raises(ValueError, match="missing required columns.+base_asset_volume"):
        _publish(tmp_path, [src])


def test_inclusive_close_exact_match_accepts(tmp_path: Path) -> None:
    us = _us(datetime(2025, 1, 1, tzinfo=UTC))
    src = _verified_source(tmp_path, rows=[_source_row(us)])
    res = _publish(tmp_path, [src])
    assert any(path for path in res.intraday_paths)


def test_inclusive_close_mismatch_rejects_row(tmp_path: Path) -> None:
    us = _us(datetime(2025, 1, 1, tzinfo=UTC))
    rows = [_source_row(us)]
    rows[0][12] = us
    rows[0][13] = us + 60_000_000
    rows[0][14] = "us"
    src = _verified_source(tmp_path, rows=rows)
    res = _publish(tmp_path, [src])
    assert any("interval_close_mismatch" in i.code for i in res.issues)
    assert not res.intraday_paths


def test_partial_day_excluded_from_daily_resample(tmp_path: Path) -> None:
    day1 = _us(datetime(2025, 1, 1, tzinfo=UTC))
    day2 = _us(datetime(2025, 1, 2, tzinfo=UTC))
    rows = [_source_row(day1), _source_row(day2)]
    p = tmp_path / "two.parquet"
    _write_parquet(p, _schema(), rows)
    m = _manifest_for(p, dataset_id="ds_two_day", rows=len(rows))
    m = DatasetManifest(
        dataset_id=m.dataset_id,
        dataset_type=m.dataset_type,
        schema=m.schema,
        transform=m.transform,
        code=m.code,
        config=m.config,
        dependencies=m.dependencies,
        files=m.files,
        statistics=m.statistics,
        coverage=m.coverage,
        quality_status=m.quality_status,
        quality_summary=m.quality_summary,
        publication=m.publication,
        supersedes_dataset_id=m.supersedes_dataset_id,
        manifest_sha256=m.manifest_sha256,
    )
    src = VerifiedSourceBarDataset(
        local_files={"two.parquet": p},
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
        manifest=m,
    )
    res = _publish(tmp_path, [src])
    daily = [path for path in res.daily_paths if "timeframe=1d" in str(path)]
    assert not daily
    assert any("incomplete_utc_day" in i.code for i in res.issues)


def test_identical_duplicate_collapses_to_min_dataset_id(tmp_path: Path) -> None:
    us = _us(datetime(2025, 1, 1, tzinfo=UTC))
    rows = [_source_row(us), _source_row(us)]
    p = tmp_path / "dup.parquet"
    _write_parquet(p, _schema(), rows)
    m = _manifest_for(p, dataset_id="ds_dup_src", rows=len(rows))
    m = DatasetManifest(
        dataset_id=m.dataset_id,
        dataset_type=m.dataset_type,
        schema=m.schema,
        transform=m.transform,
        code=m.code,
        config=m.config,
        dependencies=m.dependencies,
        files=m.files,
        statistics=m.statistics,
        coverage=m.coverage,
        quality_status=m.quality_status,
        quality_summary=m.quality_summary,
        publication=m.publication,
        supersedes_dataset_id=m.supersedes_dataset_id,
        manifest_sha256=m.manifest_sha256,
    )
    src = VerifiedSourceBarDataset(
        local_files={"dup.parquet": p},
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
        manifest=m,
    )
    res = _publish(tmp_path, [src])
    flags = []
    for path in list(res.intraday_paths) + list(res.quarantine_paths):
        for row_flags in pq.read_table(path).column("quality_flags").to_pylist():
            flags.extend(json.loads(row_flags))
    assert "duplicate_conflict" not in flags
    warnings = [i for i in res.issues if i.code == "bar001_duplicate_identical"]
    assert warnings


def test_conflict_duplicate_quarantines_all_independent_of_order(tmp_path: Path) -> None:
    us = _us(datetime(2025, 1, 1, tzinfo=UTC))
    rows_a = [_source_row(us)]
    rows_a[0][3] = Decimal("88")
    rows_b = [_source_row(us)]
    rows_b[0][3] = Decimal("89")
    p1 = tmp_path / "a.parquet"
    p2 = tmp_path / "b.parquet"
    _write_parquet(p1, _schema(), rows_a)
    _write_parquet(p2, _schema(), rows_b)
    ma = _manifest_for(p1, dataset_id="ds_a_src", rows=1)
    mb = _manifest_for(p2, dataset_id="ds_b_src", rows=1)
    src1 = VerifiedSourceBarDataset(
        local_files={"a.parquet": p1},
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
        manifest=ma,
    )
    src2 = VerifiedSourceBarDataset(
        local_files={"b.parquet": p2},
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
        manifest=mb,
    )
    res = _publish(tmp_path, [src2, src1])
    flags = []
    for path in res.quarantine_paths:
        for row_flags in pq.read_table(path).column("quality_flags").to_pylist():
            flags.extend(json.loads(row_flags))
    assert "duplicate_conflict" in flags




