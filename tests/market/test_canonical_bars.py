"""Focused BAR-001 v3 regressions for canonical bar publisher.

Covers verified MAN-001 trust, PASS_WITH_WARNINGS propagation, nullable
missing fields, strict COIN-M schema rejection, inclusive-close validation,
complete UTC days, deterministic duplicate collapse, conflict quarantine,
and legacy v1 identity rejection.

Transform: `canonical_bar_publisher` v3
Schema: `market_bar` v2
"""
from __future__ import annotations

import dataclasses
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from decimal import Decimal
from typing import Any, Sequence

from cryptofactors.catalog.dataset.canonicalize import compute_manifest_sha256, compute_dataset_id, identity_payload
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
    VerifiedDailySource,
    CanonicalBarPublishResult,
    VerifiedSourceBarDataset,
    publish_canonical_bars,
)

TEST_CODE_COMMIT = "0" * 40
TEST_CONFIG_HASH = "a" * 64
UTC = timezone.utc


def _us(ts: datetime) -> int:
    return int(ts.timestamp() * 1_000_000)


def _build_manifest(
    path: Path,
    
    dataset_id: str,
    rows: int,
    relative_path: str = "bars.parquet",
    
    venue_id: str = "binance",
    instrument_id: int = 1,
    market_type: str = "spot",
    interval: str = "1m",
    schema_variant: str = "quote_notional",
) -> DatasetManifest:
    file_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    file_bytes = path.stat().st_size
    spec = OutputFileSpec(
        relative_path=relative_path,
        sha256=file_sha,
        rows=rows,
        bytes=file_bytes,
        rows_verified=True,
        partition={
            "venue_id": venue_id,
            "instrument_id": str(instrument_id),
            "market_type": market_type,
            "interval": interval,
            "schema_variant": schema_variant,
        },
    )
    m = DatasetManifest(
        files=(spec,),
        dataset_id="__tmp__",
        dataset_type="binance_kline_source",
        schema=SchemaIdentity(name="binance_kline_source", version="2", fingerprint="fp"),
        transform=TransformSpec(name="binance_kline_source_transform", version="4"),
        code=CodeIdentity(commit=TEST_CODE_COMMIT),
        config=ConfigIdentity(config_sha256=TEST_CONFIG_HASH),
        dependencies=(),
        statistics=DatasetStatistics(row_count=rows, byte_size=file_bytes),
        coverage=CoverageWindow(
            event_start=datetime(2025, 1, 1, tzinfo=UTC),
            event_end=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={"source": "synthetic"},
        publication=PublicationMetadata(created_at=datetime(2025, 1, 1, tzinfo=UTC)),
        supersedes_dataset_id=None,
        manifest_sha256="",
    )
    expected_id, _ = compute_dataset_id(
        identity_payload(
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
            quality_summary=dict(m.quality_summary),
            supersedes_dataset_id=m.supersedes_dataset_id,
        )
    )
    m2 = dataclasses.replace(m, dataset_id=expected_id)
    computed_sha = compute_manifest_sha256(m2)
    return dataclasses.replace(m2, manifest_sha256=computed_sha)


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
        supersedes_dataset_id=manifest.supersedes_dataset_id,
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
        ("quote_volume", pa.decimal128(38, 18)),
        ("base_asset_volume", pa.decimal128(38, 18)),
        ("trades", pa.int64()),
        ("taker_buy_base_asset_volume", pa.decimal128(38, 18)),
        ("taker_buy_quote_volume", pa.decimal128(38, 18)),
        ("close_time", pa.int64()),
        ("source_open_time", pa.int64()),
        ("source_close_time", pa.int64()),
        ("source_timestamp_unit", pa.string()),
    ])


def _write_parquet(path: Path, schema: pa.Schema, rows: list[list[Any]]) -> None:
    arrays = {f.name: pa.array([r[i] for r in rows], type=f.type) for i, f in enumerate(schema)}
    pq.write_table(pa.table(arrays, schema=schema), path)


def _source_row(open_us: int, interval: str = "1m") -> list[Any]:
    if interval == "1m":
        close_us = open_us + 60_000_000 - 1
    elif interval == "1h":
        close_us = open_us + 3_600_000_000 - 1
    else:
        close_us = open_us + 86_400_000_000 - 1
    return [
        open_us, Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105"),
        Decimal("1000"), Decimal("105000"), Decimal("1000"), 10,
        Decimal("2"), Decimal("500"), close_us,
        open_us, close_us, "us",
    ]


def _source_dataset(
    tmp_path: Path,
    
    rows: list[list[Any]] | None = None,
    relative_path: str = "bars.parquet",
    quote_notional: bool = True,
) -> VerifiedSourceBarDataset:
    p = tmp_path / relative_path
    if rows is None:
        rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    _write_parquet(p, _schema(quote_notional), rows)
    m = _build_manifest(p, dataset_id="ds_" + hashlib.sha256(relative_path.encode()).hexdigest()[:38], rows=len(rows), relative_path=relative_path, market_type="spot", interval="1m", schema_variant="quote_notional")
    rcpt = _receipt_for(m)
    return VerifiedSourceBarDataset(
        local_files={relative_path: p},
        receipt=rcpt,
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
        schema_variant="quote_notional" if quote_notional else "coin_margined",
    )


def _publish(tmp_path: Path, sources: list[VerifiedSourceBarDataset], *, native_daily: Sequence[VerifiedDailySource] | None = None, **kwargs: Any) -> CanonicalBarPublishResult:
    out = tmp_path / "market_out"
    out.mkdir(exist_ok=True)
    return publish_canonical_bars(
        sources, output_dir=out, code_commit=TEST_CODE_COMMIT, native_daily=native_daily or None, **kwargs
    )


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------
def test_reject_empty_sources(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one verified source_dataset is required"):
        publish_canonical_bars([], output_dir=tmp_path, code_commit=TEST_CODE_COMMIT)


def test_reject_unverified_receipt(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id="unverified", rows=1)
    bad = dataclasses.replace(_receipt_for(m), publication_verified=False)
    src = VerifiedSourceBarDataset(
        local_files={"bars.parquet": p},
        receipt=bad,
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
    )
    with pytest.raises(ValueError, match="DatasetPublicationReceipt must be complete"):
        _publish(tmp_path, [src])


def test_pass_with_warnings_propagates(tmp_path: Path) -> None:
    base_us = _us(datetime(2025, 1, 1, tzinfo=UTC))
    rows = [_source_row(base_us + i * 60_000_000) for i in range(1440)]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id="warn", rows=len(rows))
    rcpt = dataclasses.replace(
        _receipt_for(m),
        quality_status=QualityStatus.PASS_WITH_WARNINGS,
        quality_summary={"source": "synthetic", "warning": "coverage gap"},
    )
    src = VerifiedSourceBarDataset(
        local_files={"bars.parquet": p},
        receipt=rcpt,
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
    )
    res = _publish(tmp_path, [src])
    assert res.publish_plan.quality_status is QualityStatus.PASS_WITH_WARNINGS
    assert any(i.code == "bar001_source_pass_with_warnings" for i in res.issues)


def test_nullable_missing_fields_quarantine(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    rows[0][6] = None
    rows[0][10] = None
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    src = _source_dataset(tmp_path, rows=rows)
    res = _publish(tmp_path, [src])
    assert any("bar001_source_row_parse_failure" in i.code for i in res.issues)


def test_strict_coin_m_schema_rejection(tmp_path: Path) -> None:
    schema_pq = pa.schema([
        ("open_time", pa.int64()),
        ("open", pa.decimal128(38, 18)),
        ("high", pa.decimal128(38, 18)),
        ("low", pa.decimal128(38, 18)),
        ("close", pa.decimal128(38, 18)),
        ("volume", pa.decimal128(38, 18)),
        ("quote_volume", pa.decimal128(38, 18)),
        ("trades", pa.int64()),
        ("taker_buy_base_asset_volume", pa.decimal128(38, 18)),
        ("taker_buy_quote_volume", pa.decimal128(38, 18)),
        ("close_time", pa.int64()),
        ("source_open_time", pa.int64()),
        ("source_close_time", pa.int64()),
        ("source_timestamp_unit", pa.string()),
    ])
    rows = [[_us(datetime(2025, 1, 1, tzinfo=UTC)), Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105"), Decimal("1000"), Decimal("105000"), 10, Decimal("2"), Decimal("500"), _us(datetime(2025, 1, 1, tzinfo=UTC)) + 60_000_000 - 1, _us(datetime(2025, 1, 1, tzinfo=UTC)), _us(datetime(2025, 1, 1, tzinfo=UTC)) + 60_000_000 - 1, "us"]]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, schema_pq, rows)
    src = VerifiedSourceBarDataset(
        local_files={"bars.parquet": p},
        manifest=_build_manifest(p, dataset_id="coinm", rows=1, market_type="coinm", schema_variant="coin_margined"),
        venue_id="binance",
        instrument_id=1,
        market_type="coinm",
        interval="1m",
        schema_variant="coin_margined",
    )
    with pytest.raises(ValueError):
        _publish(tmp_path, [src])


def test_inclusive_close_exact_match_accepts(tmp_path: Path) -> None:
    base_us = _us(datetime(2025, 1, 1, tzinfo=UTC))
    rows = [_source_row(base_us + i * 60_000_000) for i in range(1440)]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    src = _source_dataset(tmp_path, rows=rows)
    res = _publish(tmp_path, [src])
    assert res.publish_plan.quality_status is QualityStatus.PASS
    assert not any("bar001_interval_close_mismatch" in i.code for i in res.issues)


def test_inclusive_close_mismatch_rejects_row(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    rows[0][13] = _us(datetime(2025, 1, 1, tzinfo=UTC)) + 120_000_000 - 1
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    src = _source_dataset(tmp_path, rows=rows)
    res = _publish(tmp_path, [src])
    assert any("bar001_interval_close_mismatch" in i.code for i in res.issues)


def test_partial_day_excluded(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, 0, 0, tzinfo=UTC)))]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    src = _source_dataset(tmp_path, rows=rows)
    res = _publish(tmp_path, [src])
    assert res.publish_plan.quality_status is QualityStatus.REJECTED
    assert any("bar001_incomplete_utc_day" in i.code for i in res.issues)


def test_identical_duplicate_collapses(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    src1 = _source_dataset(tmp_path, rows=rows)
    src2 = _source_dataset(tmp_path, rows=rows)
    res = _publish(tmp_path, [src1, src2])
    assert len(res.intraday_paths) == 1


def test_conflict_duplicate_quarantines(tmp_path: Path) -> None:
    base = _source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))
    rows = [
        [base[0], Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105"), Decimal("1000"), Decimal("105000"), Decimal("1000"), 10, Decimal("2"), Decimal("500"), base[11], base[12], base[13], base[14]],
        [base[0], Decimal("100"), Decimal("110"), Decimal("90"), Decimal("200"), Decimal("1000"), Decimal("105000"), Decimal("1000"), 10, Decimal("2"), Decimal("500"), base[11], base[12], base[13], base[14]],
    ]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id="ds_conf", rows=len(rows))
    src = VerifiedSourceBarDataset(
        local_files={"bars.parquet": p},
        receipt=_receipt_for(m),
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
    )
    res = _publish(tmp_path, [src])
    assert any("bar001_duplicate_conflict" in i.code for i in res.issues)


def test_reject_legacy_v1_identity(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    file_sha = hashlib.sha256(p.read_bytes()).hexdigest()
    spec = OutputFileSpec(relative_path="bars.parquet", sha256=file_sha, rows=1, bytes=p.stat().st_size, rows_verified=True)
    m = DatasetManifest(
        files=(spec,),
        dataset_id="ds_legacy",
        dataset_type="normalized_source",
        schema=SchemaIdentity(name="market_bar", version="1", fingerprint="fp"),
        transform=TransformSpec(name="canonical_bar_publisher", version="1"),
        code=CodeIdentity(commit=TEST_CODE_COMMIT),
        config=ConfigIdentity(config_sha256=TEST_CONFIG_HASH),
        dependencies=(),
        statistics=DatasetStatistics(row_count=1, byte_size=p.stat().st_size),
        coverage=CoverageWindow(
            event_start=datetime(2025, 1, 1, tzinfo=UTC),
            event_end=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={},
        publication=PublicationMetadata(created_at=datetime(2025, 1, 1, tzinfo=UTC)),
        supersedes_dataset_id=None,
        manifest_sha256="",
    )
    m2 = dataclasses.replace(m, manifest_sha256=compute_manifest_sha256(m))
    src = VerifiedSourceBarDataset(
        local_files={"bars.parquet": p},
        manifest=m2,
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
    )
    with pytest.raises(ValueError, match="manifest.dataset_id disagrees with recomputed identity"):
        _publish(tmp_path, [src])
