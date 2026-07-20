"""Focused BAR-001 v5 regressions for canonical bar publisher.

Covers verified MAN-001 trust, transform v5, dataset-ID/byte-size mismatch,
unsupported identity, partition-key validation, incomplete receipt, duplicate
collapse/conflict, shifted normalized timestamps, mixed-timeframe daily
selection, daily OHLCV, native-daily reconciliation, and safe output/catalog
registration.

Transform: `canonical_bar_publisher` v5
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

from cryptofactors.catalog.dataset.canonicalize import (
    compute_manifest_sha256,
    compute_dataset_id,
    identity_payload,
)
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


def _write_parquet(path: Path, schema: pa.Schema, rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {f.name: pa.array([r[i] for r in rows], type=f.type) for i, f in enumerate(schema)}
    pq.write_table(pa.table(arrays, schema=schema), path)


def _source_row(open_us: int, interval: str = "1m") -> list:
    if interval == "1m":
        close_us = open_us + 60_000_000 - 1
    elif interval == "5m":
        close_us = open_us + 5 * 60_000_000 - 1
    else:
        close_us = open_us + 86_400_000_000 - 1
    return [
        open_us, Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105"),
        Decimal("1000"), Decimal("105000"), Decimal("1000"), 10,
        Decimal("2"), Decimal("500"), close_us,
        open_us, close_us, "us",
    ]


def _build_manifest(
    path: Path,
    *,
    dataset_id: str,
    rows: int,
    relative_path: str = "bars.parquet",
    venue_id: str = "binance",
    instrument_id: int = 1,
    market_type: str = "spot",
    interval: str = "1m",
    schema_variant: str = "quote_notional",
    dataset_type: str = "binance_kline_source",
    schema_name: str = "binance_kline_source",
    schema_version: str = "2",
    transform_version: str = "5",
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
        dataset_type=dataset_type,
        schema=SchemaIdentity(name=schema_name, version=schema_version, fingerprint="fp"),
        transform=TransformSpec(name="binance_kline_source_transform", version=transform_version),
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


def _source_dataset(
    tmp_path: Path,
    *,
    rows: list[list] | None = None,
    relative_path: str = "bars.parquet",
    quote_notional: bool = True,
    dataset_id: str | None = None,
    interval: str = "1m",
) -> VerifiedSourceBarDataset:
    p = tmp_path / relative_path
    if rows is None:
        rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)), interval=interval)]
    _write_parquet(p, _schema(quote_notional), rows)
    did = dataset_id or ("ds_" + hashlib.sha256(relative_path.encode()).hexdigest()[:38])
    m = _build_manifest(p, dataset_id=did, rows=len(rows), relative_path=relative_path,
                        market_type="spot", interval=interval, schema_variant="quote_notional")
    rcpt = _receipt_for(m)
    return VerifiedSourceBarDataset(
        local_files={relative_path: p},
        receipt=rcpt,
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval=interval,
        schema_variant="quote_notional" if quote_notional else "coin_margined",
    )


def _publish(tmp_path: Path, sources, *, native_daily=None, **kwargs) -> CanonicalBarPublishResult:
    out = tmp_path / "market_out"
    out.mkdir(parents=True, exist_ok=True)
    return publish_canonical_bars(
        sources, output_dir=out, code_commit=TEST_CODE_COMMIT,
        native_daily=native_daily or None, **kwargs
    )


# ------------------------------------------------------------------
# Item 1: module header is v5 (asserted by file docstring above);
# plus transform-version constant confirmation in a real publish.
# ------------------------------------------------------------------
def test_transform_version_constant_is_v5() -> None:
    from cryptofactors.market.bars import CANONICAL_BAR_TRANSFORM_VERSION
    assert CANONICAL_BAR_TRANSFORM_VERSION == "5"


# ------------------------------------------------------------------
# Item 2a: dataset-ID mismatch after a valid manifest hash.
# Forge only dataset_id, then re-sign manifest_sha256 over the forged body.
# ------------------------------------------------------------------
def test_dataset_id_mismatch_rejected(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id="ds_real", rows=1)
    forged = dataclasses.replace(m, dataset_id="ds_forged")
    forged = dataclasses.replace(forged, manifest_sha256=compute_manifest_sha256(forged))
    rcpt = _receipt_for(m)
    rcpt = dataclasses.replace(rcpt, dataset_id="ds_forged", manifest_sha256=forged.manifest_sha256)
    src = VerifiedSourceBarDataset(
        local_files={"bars.parquet": p},
        receipt=rcpt,
        manifest=forged,
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
    )
    with pytest.raises(ValueError, match="manifest.dataset_id disagrees with recomputed identity"):
        _publish(tmp_path, [src])


# ------------------------------------------------------------------
# Item 2b: byte-size mismatch after a valid file hash.
# Preserve real file SHA; change declared byte count, re-sign identity,
# and propagate the new recomputed dataset_id to the receipt so the
# identity check passes and the file byte-size check fires at runtime.
# ------------------------------------------------------------------
def test_byte_size_mismatch_rejected(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id="ds_size", rows=1)
    bad_spec = dataclasses.replace(m.files[0], bytes=m.files[0].bytes + 1)
    bad = dataclasses.replace(
        m,
        files=(bad_spec,),
        statistics=DatasetStatistics(row_count=m.statistics.row_count, byte_size=m.statistics.byte_size + 1),
    )
    expected_id, _ = compute_dataset_id(
        identity_payload(
            dataset_type=bad.dataset_type, schema=bad.schema, transform=bad.transform, code=bad.code,
            config=bad.config, dependencies=bad.dependencies, files=bad.files, statistics=bad.statistics,
            coverage=bad.coverage, quality_status=bad.quality_status, quality_summary=dict(bad.quality_summary),
            supersedes_dataset_id=bad.supersedes_dataset_id,
        )
    )
    bad = dataclasses.replace(bad, dataset_id=expected_id)
    bad = dataclasses.replace(bad, manifest_sha256=compute_manifest_sha256(bad))
    rcpt = dataclasses.replace(
        _receipt_for(bad),
        dataset_id=expected_id,
        manifest_sha256=bad.manifest_sha256,
    )
    src = VerifiedSourceBarDataset(
        local_files={"bars.parquet": p},
        receipt=rcpt,
        manifest=bad,
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
    )
    with pytest.raises(ValueError, match="byte size mismatch"):
        _publish(tmp_path, [src])


# ------------------------------------------------------------------
# Item 2c: unsupported dataset type (reachable: change one identity field,
# re-sign dataset_id + manifest hash).
# ------------------------------------------------------------------
def test_unsupported_dataset_type_rejected(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id="ds_type", rows=1, dataset_type="unsupported_source")
    with pytest.raises(ValueError, match="unsupported source dataset_type"):
        _publish(tmp_path, [VerifiedSourceBarDataset(
            local_files={"bars.parquet": p},
            manifest=m,
            venue_id="binance",
            instrument_id=1,
            market_type="spot",
            interval="1m",
        )])


# ------------------------------------------------------------------
# Item 2d: unsupported schema version (reachable: change schema version,
# re-sign dataset_id + manifest hash).
# ------------------------------------------------------------------
def test_unsupported_schema_version_rejected(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id="ds_schemav", rows=1, schema_version="99")
    with pytest.raises(ValueError, match="unsupported source schema"):
        _publish(tmp_path, [VerifiedSourceBarDataset(
            local_files={"bars.parquet": p},
            manifest=m,
            venue_id="binance",
            instrument_id=1,
            market_type="spot",
            interval="1m",
        )])


# ------------------------------------------------------------------
# Item 3: every required partition key independently missing and mismatched.
# ------------------------------------------------------------------
_REQUIRED_PARTITION_KEYS = ("venue_id", "market_type", "interval", "instrument_id", "schema_variant")


def _manifest_with_partition(partition: dict) -> DatasetManifest:
    p = Path("/tmp/part_probe/bars.parquet")
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        _write_parquet(p, _schema(), [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))])
    spec = OutputFileSpec(
        relative_path="bars.parquet",
        sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        rows=1,
        bytes=p.stat().st_size,
        rows_verified=True,
        partition=partition,
    )
    m = DatasetManifest(
        files=(spec,),
        dataset_id="__tmp__",
        dataset_type="binance_kline_source",
        schema=SchemaIdentity(name="binance_kline_source", version="2", fingerprint="fp"),
        transform=TransformSpec(name="binance_kline_source_transform", version="5"),
        code=CodeIdentity(commit=TEST_CODE_COMMIT),
        config=ConfigIdentity(config_sha256=TEST_CONFIG_HASH),
        dependencies=(),
        statistics=DatasetStatistics(row_count=1, byte_size=p.stat().st_size),
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
            dataset_type=m.dataset_type, schema=m.schema, transform=m.transform, code=m.code,
            config=m.config, dependencies=m.dependencies, files=m.files, statistics=m.statistics,
            coverage=m.coverage, quality_status=m.quality_status, quality_summary=dict(m.quality_summary),
            supersedes_dataset_id=m.supersedes_dataset_id,
        )
    )
    m2 = dataclasses.replace(m, dataset_id=expected_id)
    return dataclasses.replace(m2, manifest_sha256=compute_manifest_sha256(m2))


def _good_partition() -> dict:
    return {
        "venue_id": "binance",
        "market_type": "spot",
        "interval": "1m",
        "instrument_id": "1",
        "schema_variant": "quote_notional",
    }


def test_partition_key_missing_rejected(tmp_path: Path) -> None:
    for key in _REQUIRED_PARTITION_KEYS:
        part = _good_partition()
        del part[key]
        m = _manifest_with_partition(part)
        with pytest.raises(ValueError, match="missing required partition key"):
            _publish(tmp_path, [VerifiedSourceBarDataset(
                local_files={"bars.parquet": Path("/tmp/part_probe/bars.parquet")},
                manifest=m,
                venue_id="binance",
                instrument_id=1,
                market_type="spot",
                interval="1m",
            )])


def test_partition_key_mismatched_rejected(tmp_path: Path) -> None:
    mismatches = {
        "venue_id": "kraken",
        "market_type": "usdm",
        "interval": "5m",
        "instrument_id": "2",
        "schema_variant": "coin_margined",
    }
    for key in _REQUIRED_PARTITION_KEYS:
        part = _good_partition()
        part[key] = mismatches[key]
        m = _manifest_with_partition(part)
        with pytest.raises(ValueError, match="disagrees with verified partition"):
            _publish(tmp_path, [VerifiedSourceBarDataset(
                local_files={"bars.parquet": Path("/tmp/part_probe/bars.parquet")},
                manifest=m,
                venue_id="binance",
                instrument_id=1,
                market_type="spot",
                interval="1m",
            )])


# ------------------------------------------------------------------
# Item 4: incomplete-receipt evidence beyond publication_verified=False.
# ------------------------------------------------------------------
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


def test_reject_receipt_missing_manifest_sha256(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id="nohash", rows=1)
    bad = dataclasses.replace(_receipt_for(m), manifest_sha256="")
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


def test_reject_receipt_bad_dataset_id_prefix(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id="badid", rows=1)
    bad = dataclasses.replace(_receipt_for(m), dataset_id="xx_not_ds_prefixed")
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


# ------------------------------------------------------------------
# Item 5: duplicate collapse/conflict with distinct valid dataset IDs in
# both source orders (different relative paths -> distinct dataset IDs).
# ------------------------------------------------------------------
def test_identical_duplicate_collapses_both_orders(tmp_path: Path) -> None:
    rows_a = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    rows_b = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    src_a = _source_dataset(tmp_path, rows=rows_a, relative_path="a/bars.parquet", dataset_id="ds_a")
    src_b = _source_dataset(tmp_path, rows=rows_b, relative_path="b/bars.parquet", dataset_id="ds_b")
    res_ab = _publish(tmp_path, [src_a, src_b])
    res_ba = _publish(tmp_path, [src_b, src_a])
    assert len(res_ab.intraday_paths) == 1
    assert len(res_ba.intraday_paths) == 1


def test_conflict_duplicate_quarantines_both_orders(tmp_path: Path) -> None:
    base = _source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))
    rows_a = [
        [base[0], Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105"), Decimal("1000"),
         Decimal("105000"), Decimal("1000"), 10, Decimal("2"), Decimal("500"), base[11], base[12], base[13], base[14]],
    ]
    rows_b = [
        [base[0], Decimal("100"), Decimal("110"), Decimal("90"), Decimal("200"), Decimal("1000"),
         Decimal("105000"), Decimal("1000"), 10, Decimal("2"), Decimal("500"), base[11], base[12], base[13], base[14]],
    ]
    pa_ = tmp_path / "a/bars.parquet"
    pb = tmp_path / "b/bars.parquet"
    _write_parquet(pa_, _schema(), rows_a)
    _write_parquet(pb, _schema(), rows_b)
    m_a = _build_manifest(pa_, dataset_id="ds_conf_a", rows=1, relative_path="a/bars.parquet")
    m_b = _build_manifest(pb, dataset_id="ds_conf_b", rows=1, relative_path="b/bars.parquet")
    src_a = VerifiedSourceBarDataset(local_files={"a/bars.parquet": pa_}, receipt=_receipt_for(m_a),
                                     venue_id="binance", instrument_id=1, market_type="spot", interval="1m")
    src_b = VerifiedSourceBarDataset(local_files={"b/bars.parquet": pb}, receipt=_receipt_for(m_b),
                                     venue_id="binance", instrument_id=1, market_type="spot", interval="1m")
    res_ab = _publish(tmp_path, [src_a, src_b])
    res_ba = _publish(tmp_path, [src_b, src_a])
    assert any("bar001_duplicate_conflict" in i.code for i in res_ab.issues)
    assert any("bar001_duplicate_conflict" in i.code for i in res_ba.issues)
    assert len(res_ab.intraday_paths) == 0


# ------------------------------------------------------------------
# Item 6: shifted normalized timestamps with valid source boundary arithmetic.
# ------------------------------------------------------------------
def test_shifted_normalized_timestamp_mismatch_quarantines(tmp_path: Path) -> None:
    open_us = _us(datetime(2025, 1, 1, tzinfo=UTC))
    sot = open_us
    sct = open_us + 60_000_000 - 1
    close_us_shifted = open_us + 1_000_000  # shifted normalized close
    rows = [[open_us, Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105"),
             Decimal("1000"), Decimal("105000"), Decimal("1000"), 10,
             Decimal("2"), Decimal("500"), close_us_shifted,
             sot, sct, "us"]]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id="ds_shift", rows=1)
    src = VerifiedSourceBarDataset(local_files={"bars.parquet": p}, receipt=_receipt_for(m),
                                   venue_id="binance", instrument_id=1, market_type="spot", interval="1m")
    res = _publish(tmp_path, [src])
    assert any("bar001_normalized_source_timestamp_mismatch" in i.code for i in res.issues)


# ------------------------------------------------------------------
# Item 7: simultaneous complete 1m/5m days -> ambiguity, explicit 1m
# selection, and no merge.
# ------------------------------------------------------------------
def _full_day_rows(interval: str) -> list[list]:
    step = 60_000_000 if interval == "1m" else 5 * 60_000_000
    base = _us(datetime(2025, 1, 1, tzinfo=UTC))
    n = (86_400_000_000 // step)
    return [_source_row(base + i * step, interval=interval) for i in range(n)]


def test_mixed_timeframe_ambiguity_fails_closed(tmp_path: Path) -> None:
    rows_1m = _full_day_rows("1m")
    rows_5m = _full_day_rows("5m")
    src_1m = _source_dataset(tmp_path, rows=rows_1m, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_1m")
    src_5m = _source_dataset(tmp_path, rows=rows_5m, relative_path="m5/bars.parquet", interval="5m", dataset_id="ds_5m")
    with pytest.raises(ValueError, match="ambiguous multiple complete source timeframes"):
        _publish(tmp_path, [src_1m, src_5m])


def test_explicit_1m_selection_no_merge(tmp_path: Path) -> None:
    rows_1m = _full_day_rows("1m")
    rows_5m = _full_day_rows("5m")
    src_1m = _source_dataset(tmp_path, rows=rows_1m, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_1m")
    src_5m = _source_dataset(tmp_path, rows=rows_5m, relative_path="m5/bars.parquet", interval="5m", dataset_id="ds_5m")
    res = _publish(tmp_path, [src_1m, src_5m], daily_source_timeframe="1m")
    # daily should be resampled from 1m only: 1 day -> 1 daily bar.
    assert len(res.daily_paths) == 1
    plan = res.publish_plan
    assert plan.quality_summary["daily_source_timeframe"] == "1m"


def test_no_merge_mixed_timeframe_daily_counts(tmp_path: Path) -> None:
    rows_1m = _full_day_rows("1m")
    src_1m = _source_dataset(tmp_path, rows=rows_1m, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_1m_only")
    res = _publish(tmp_path, [src_1m], daily_source_timeframe="1m")
    # 1m day resampled -> exactly 1 daily bar (1d).
    daily = pq.read_table(str(res.daily_paths[0]))
    assert daily.num_rows == 1


# ------------------------------------------------------------------
# Item 8: assert daily OHLCV values.
# ------------------------------------------------------------------
def test_daily_ohlcv_values(tmp_path: Path) -> None:
    rows = _full_day_rows("1m")
    src = _source_dataset(tmp_path, rows=rows, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_ohlcv")
    res = _publish(tmp_path, [src], daily_source_timeframe="1m")
    assert len(res.daily_paths) == 1
    daily = pq.read_table(str(res.daily_paths[0]))
    assert daily.num_rows == 1
    col = {n: daily.column(n)[0].as_py() for n in daily.column_names}
    # open = first 1m open, close = last 1m close, high/low across day.
    assert col["open"] == Decimal("100")
    assert col["close"] == Decimal("105")
    assert col["high"] == Decimal("110")
    assert col["low"] == Decimal("90")
    assert col["timeframe"] == "1d"


# ------------------------------------------------------------------
# Item 9: native-daily reconciliation outcomes: match, mismatch, missing
# native, missing resampled.
# ------------------------------------------------------------------
def _native_daily_source(tmp_path: Path, day_open_us: int, close: Decimal, dataset_id: str) -> VerifiedDailySource:
    rows = [[day_open_us, Decimal("100"), Decimal("110"), Decimal("90"), close,
             Decimal("1000"), Decimal("105000"), Decimal("1000"), 10,
             Decimal("2"), Decimal("500"), day_open_us + 86_400_000_000 - 1,
             day_open_us, day_open_us + 86_400_000_000 - 1, "us"]]
    p = tmp_path / f"native_{dataset_id}/bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id=dataset_id, rows=1, relative_path=f"native_{dataset_id}/bars.parquet", interval="1d")
    return VerifiedDailySource(local_files={f"native_{dataset_id}/bars.parquet": p}, receipt=_receipt_for(m),
                               venue_id="binance", instrument_id=1, market_type="spot")


def test_reconcile_match(tmp_path: Path) -> None:
    rows = _full_day_rows("1m")
    src = _source_dataset(tmp_path, rows=rows, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_rm")
    native = _native_daily_source(tmp_path, _us(datetime(2025, 1, 1, tzinfo=UTC)), Decimal("105"), "ds_nat_match")
    res = _publish(tmp_path, [src], native_daily=[native], daily_source_timeframe="1m",
                   price_tolerance=Decimal("1"), volume_tolerance=Decimal("10_000_000_000"))
    assert len(res.daily_paths) == 1
    assert not any("bar001_daily_reconcile_mismatch" in i.code for i in res.issues)


def test_reconcile_mismatch_quarantine(tmp_path: Path) -> None:
    rows = _full_day_rows("1m")
    src = _source_dataset(tmp_path, rows=rows, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_rmm")
    native = _native_daily_source(tmp_path, _us(datetime(2025, 1, 1, tzinfo=UTC)), Decimal("999"), "ds_nat_mismatch")
    res = _publish(tmp_path, [src], native_daily=[native], daily_source_timeframe="1m")
    assert any("bar001_daily_reconcile_mismatch" in i.code for i in res.issues)
    # mismatched resampled daily not promoted to accepted daily paths.
    assert len(res.daily_paths) == 0
    assert len(res.reconcile_paths) == 1


def test_reconcile_missing_native(tmp_path: Path) -> None:
    rows = _full_day_rows("1m")
    src = _source_dataset(tmp_path, rows=rows, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_rmn")
    res = _publish(tmp_path, [src], daily_source_timeframe="1m")
    # No native daily supplied -> resampled daily still promoted; reconcile report empty.
    assert len(res.daily_paths) == 1
    assert len(res.reconcile_paths) == 1
    rep = pq.read_table(str(res.reconcile_paths[0]))
    assert rep.num_rows == 0


def test_reconcile_missing_resampled(tmp_path: Path) -> None:
    # Native daily present but no resampled intraday daily (only partial intraday).
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    src = _source_dataset(tmp_path, rows=rows, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_rmr")
    native = _native_daily_source(tmp_path, _us(datetime(2025, 1, 1, tzinfo=UTC)), Decimal("105"), "ds_nat_only")
    res = _publish(tmp_path, [src], native_daily=[native], daily_source_timeframe="1m")
    # resampled incomplete -> no daily path; reconcile reports native_only.
    assert len(res.daily_paths) == 0
    rep = pq.read_table(str(res.reconcile_paths[0]))
    statuses = set(rep.column("status").to_pylist())
    assert "missing_resampled" in statuses


# ------------------------------------------------------------------
# Item 10: safe paths, partition measurements, row/dependency lineage,
# verify_outputs, and successful catalog-registered DatasetPublisher.publish.
# ------------------------------------------------------------------
def test_safe_output_paths_and_partition_measurements(tmp_path: Path) -> None:
    rows = _full_day_rows("1m")
    src = _source_dataset(tmp_path, rows=rows, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_safe")
    res = _publish(tmp_path, [src], daily_source_timeframe="1m")
    # safe nested partition layout
    assert all("venue_id=binance" in str(p) for p in res.intraday_paths + res.daily_paths)
    assert all(p.name == "bars.parquet" for p in res.intraday_paths + res.daily_paths)
    # partition measurements present for intraday + daily
    kinds = {m.kind for m in res.partition_sizes}
    assert "intraday" in kinds
    assert "daily" in kinds
    assert all(m.rows > 0 for m in res.partition_sizes if m.kind in ("intraday", "daily"))


def test_row_and_dependency_lineage(tmp_path: Path) -> None:
    rows = _full_day_rows("1m")
    src = _source_dataset(tmp_path, rows=rows, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_lineage")
    res = _publish(tmp_path, [src], daily_source_timeframe="1m")
    # exactly one source dependency edge carries a valid ds_ id
    dep_ids = {d.id for d in res.publish_plan.dependencies}
    assert len(dep_ids) == 1
    assert all(d.id.startswith("ds_") for d in res.publish_plan.dependencies)
    # canonical bar rows carry source_dataset_id lineage matching the dependency
    intraday = pq.read_table(str(res.intraday_paths[0]))
    assert "source_dataset_id" in intraday.column_names
    assert intraday.column("source_dataset_id")[0].as_py() == next(iter(dep_ids))


def test_verify_outputs_passes(tmp_path: Path) -> None:
    from cryptofactors.catalog.dataset.outputs import verify_outputs
    from cryptofactors.catalog.dataset.models import RowCountPolicy
    rows = _full_day_rows("1m")
    src = _source_dataset(tmp_path, rows=rows, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_verify")
    res = _publish(tmp_path, [src], daily_source_timeframe="1m")
    plan = res.publish_plan
    verified = verify_outputs(
        sources=dict(plan.output_sources),
        specs=list(plan.output_specs),
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters=dict(plan.row_counters),
    )
    assert len(verified) == len(plan.output_specs)


def test_catalog_registered_publish(tmp_path: Path) -> None:
    from cryptofactors.catalog.dataset.outputs import verify_outputs
    from cryptofactors.catalog.dataset.publisher import DatasetPublisher
    from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
    from cryptofactors.catalog.dataset.models import RowCountPolicy, DatasetStoreConfig
    from cryptofactors.catalog.runner import apply_migrations, MIGRATIONS_DIR

    rows = _full_day_rows("1m")
    p = tmp_path / "m1/bars.parquet"
    _write_parquet(p, _schema(), rows)
    sm = _build_manifest(p, dataset_id="ds_pub", rows=len(rows), relative_path="m1/bars.parquet",
                         market_type="spot", interval="1m", schema_variant="quote_notional")
    src = VerifiedSourceBarDataset(
        local_files={"m1/bars.parquet": p},
        receipt=_receipt_for(sm),
        venue_id="binance", instrument_id=1, market_type="spot", interval="1m",
        schema_variant="quote_notional",
    )
    res = _publish(tmp_path, [src], daily_source_timeframe="1m")
    plan = res.publish_plan
    verify_outputs(
        sources=dict(plan.output_sources),
        specs=list(plan.output_specs),
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters=dict(plan.row_counters),
    )

    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    cat = SqliteDatasetCatalog(db)
    cat._conn.execute(
        "INSERT OR IGNORE INTO source (source_id, source_type, official_url, terms_class, config_json, created_at) VALUES (?, 'external', NULL, NULL, '{}', ?)",
        ("binance", datetime.now(timezone.utc).isoformat()),
    )
    # Register the upstream source dataset so dependency validation passes.
    cat._conn.execute(
        """INSERT OR IGNORE INTO dataset (
            dataset_id, dataset_type, schema_version, schema_fingerprint,
            manifest_sha256, manifest_uri, publication_uri,
            transform_name, transform_version, code_commit, config_sha256,
            row_count, byte_size, event_start, event_end, availability_start,
            availability_end, quality_status, quality_summary_json,
            supersedes_dataset_id, publication_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            sm.dataset_id, sm.dataset_type, sm.schema.version, sm.schema.fingerprint,
            sm.manifest_sha256, "manifest.json", "datasets/sha256",
            sm.transform.name, sm.transform.version, sm.code.commit, sm.config.config_sha256,
            sm.statistics.row_count, sm.statistics.byte_size,
            datetime(2025, 1, 1, tzinfo=UTC).isoformat(), datetime(2025, 1, 1, 0, 1, tzinfo=UTC).isoformat(),
            datetime(2025, 1, 1, tzinfo=UTC).isoformat(), datetime(2025, 1, 1, 0, 1, tzinfo=UTC).isoformat(),
            sm.quality_status.value, "{}", None, "REGISTERED", datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
        ),
    )
    cat._conn.commit()

    root = tmp_path / "store"
    root.mkdir(exist_ok=True)
    cfg = DatasetStoreConfig(root=root)
    pub = DatasetPublisher(cfg, cat)
    receipt = pub.publish(plan, register_catalog=True)
    assert receipt.dataset_id
    assert receipt.manifest_sha256
    assert receipt.catalog_registered is True


# ------------------------------------------------------------------
# Pre-existing regression coverage retained from prior Jr work.
# ------------------------------------------------------------------
def test_reject_empty_sources(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one verified source_dataset is required"):
        publish_canonical_bars([], output_dir=tmp_path, code_commit=TEST_CODE_COMMIT)


def test_pass_with_warnings_propagates(tmp_path: Path) -> None:
    rows = _full_day_rows("1m")
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    m = _build_manifest(p, dataset_id="warn", rows=len(rows))
    rcpt = dataclasses.replace(_receipt_for(m), quality_status=QualityStatus.PASS_WITH_WARNINGS,
                               quality_summary={"source": "synthetic", "warning": "coverage gap"})
    src = VerifiedSourceBarDataset(local_files={"bars.parquet": p}, receipt=rcpt,
                                   venue_id="binance", instrument_id=1, market_type="spot", interval="1m")
    res = _publish(tmp_path, [src])
    assert res.publish_plan.quality_status is QualityStatus.PASS_WITH_WARNINGS
    assert any(i.code == "bar001_source_pass_with_warnings" for i in res.issues)


def test_nullable_missing_fields_quarantine(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    rows[0][6] = None
    rows[0][10] = None
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
    rows = [[_us(datetime(2025, 1, 1, tzinfo=UTC)), Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105"),
             Decimal("1000"), Decimal("105000"), 10, Decimal("2"), Decimal("500"),
             _us(datetime(2025, 1, 1, tzinfo=UTC)) + 60_000_000 - 1,
             _us(datetime(2025, 1, 1, tzinfo=UTC)), _us(datetime(2025, 1, 1, tzinfo=UTC)) + 60_000_000 - 1, "us"]]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, schema_pq, rows)
    src = VerifiedSourceBarDataset(
        local_files={"bars.parquet": p},
        manifest=_build_manifest(p, dataset_id="coinm", rows=1, market_type="coinm", schema_variant="coin_margined"),
        venue_id="binance", instrument_id=1, market_type="coinm", interval="1m", schema_variant="coin_margined",
    )
    with pytest.raises(ValueError):
        _publish(tmp_path, [src])


def test_inclusive_close_exact_match_accepts(tmp_path: Path) -> None:
    rows = _full_day_rows("1m")
    src = _source_dataset(tmp_path, rows=rows, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_close_ok")
    res = _publish(tmp_path, [src], daily_source_timeframe="1m")
    assert res.publish_plan.quality_status is QualityStatus.PASS
    assert not any("bar001_interval_close_mismatch" in i.code for i in res.issues)


def test_inclusive_close_mismatch_rejects_row(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    rows[0][13] = _us(datetime(2025, 1, 1, tzinfo=UTC)) + 120_000_000 - 1
    src = _source_dataset(tmp_path, rows=rows)
    res = _publish(tmp_path, [src])
    assert any("bar001_interval_close_mismatch" in i.code for i in res.issues)


def test_partial_day_excluded(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, 0, 0, tzinfo=UTC)))]
    src = _source_dataset(tmp_path, rows=rows)
    res = _publish(tmp_path, [src])
    assert res.publish_plan.quality_status is QualityStatus.REJECTED
    assert any("bar001_incomplete_utc_day" in i.code for i in res.issues)


def test_forged_manifest_hash_and_dataset_id_rejected(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p2 = tmp_path / "bars.parquet"
    _write_parquet(p2, _schema(), rows)
    m = _build_manifest(p2, dataset_id="ds_hash", rows=1)
    bad_m = dataclasses.replace(m, manifest_sha256="0" * 64, dataset_id="ds_bad")
    rcpt = _receipt_for(m)
    rcpt = dataclasses.replace(rcpt, manifest_sha256="0" * 64, dataset_id="ds_bad")
    src = VerifiedSourceBarDataset(
        local_files={"bars.parquet": p2},
        receipt=rcpt,
        manifest=bad_m,
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
    )
    with pytest.raises(ValueError, match="manifest_sha256 disagrees with recomputed body"):
        _publish(tmp_path, [src])


def test_local_file_hash_mismatch_reject(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p2 = tmp_path / "bars.parquet"
    _write_parquet(p2, _schema(), rows)
    m = _build_manifest(p2, dataset_id="ds_loc", rows=1)
    tampered = p2.with_suffix(".bad.parquet")
    tampered.write_bytes(p2.read_bytes() + b"x")
    rcpt = _receipt_for(m)
    src = VerifiedSourceBarDataset(
        local_files={"bars.parquet": tampered},
        receipt=rcpt,
        manifest=m,
        venue_id="binance",
        instrument_id=1,
        market_type="spot",
        interval="1m",
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        _publish(tmp_path, [src])


def test_receive_rejected_quality_fails_closed(tmp_path: Path) -> None:
    rcpt = DatasetPublicationReceipt(
        dataset_id="ds_rej",
        manifest_sha256="a" * 64,
        manifest_uri="manifest.json",
        publication_uri="datasets/sha256",
        dataset_path=Path("/tmp"),
        verified_outputs=(),
        publication_verified=True,
        object_prefix="datasets/sha256",
        dependencies=(),
        supersedes_dataset_id=None,
        dataset_type="binance_kline_source",
        schema=SchemaIdentity(name="binance_kline_source", version="2", fingerprint="fp"),
        transform=TransformSpec(name="canonical_bar_publisher", version="5"),
        code=CodeIdentity(commit="0" * 40),
        config=ConfigIdentity(config_sha256="a" * 64),
        statistics=DatasetStatistics(row_count=0, byte_size=0),
        coverage=CoverageWindow(event_start=datetime(2025, 1, 1, tzinfo=UTC), event_end=datetime(2025, 1, 1, 0, 1, tzinfo=UTC)),
        quality_status=QualityStatus.REJECTED,
        quality_summary={},
        catalog_created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    src = VerifiedSourceBarDataset(receipt=rcpt, venue_id="binance", instrument_id=1,
                                   market_type="spot", interval="1m", local_files={})
    with pytest.raises(ValueError, match="source dataset quality_status must be PASS or PASS_WITH_WARNINGS"):
        _publish(tmp_path, [src])


def test_receive_quarantined_quality_fails_closed(tmp_path: Path) -> None:
    rcpt = DatasetPublicationReceipt(
        dataset_id="ds_quar",
        manifest_sha256="a" * 64,
        manifest_uri="manifest.json",
        publication_uri="datasets/sha256",
        dataset_path=Path("/tmp"),
        verified_outputs=(),
        publication_verified=True,
        object_prefix="datasets/sha256",
        dependencies=(),
        supersedes_dataset_id=None,
        dataset_type="binance_kline_source",
        schema=SchemaIdentity(name="binance_kline_source", version="2", fingerprint="fp"),
        transform=TransformSpec(name="canonical_bar_publisher", version="5"),
        code=CodeIdentity(commit="0" * 40),
        config=ConfigIdentity(config_sha256="a" * 64),
        statistics=DatasetStatistics(row_count=0, byte_size=0),
        coverage=CoverageWindow(event_start=datetime(2025, 1, 1, tzinfo=UTC), event_end=datetime(2025, 1, 1, 0, 1, tzinfo=UTC)),
        quality_status=QualityStatus.QUARANTINED,
        quality_summary={},
        catalog_created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    src = VerifiedSourceBarDataset(receipt=rcpt, venue_id="binance", instrument_id=1,
                                   market_type="spot", interval="1m", local_files={})
    with pytest.raises(ValueError, match="source dataset quality_status must be PASS or PASS_WITH_WARNINGS"):
        _publish(tmp_path, [src])


def test_legacy_v1_identity_rejected(tmp_path: Path) -> None:
    rows = [_source_row(_us(datetime(2025, 1, 1, tzinfo=UTC)))]
    p = tmp_path / "bars.parquet"
    _write_parquet(p, _schema(), rows)
    file_sha = hashlib.sha256(p.read_bytes()).hexdigest()
    spec = OutputFileSpec(relative_path="bars.parquet", sha256=file_sha, rows=1, bytes=p.stat().st_size, rows_verified=True)
    m = DatasetManifest(
        files=(spec,),
        dataset_id="__tmp__",
        dataset_type="binance_kline_source",
        schema=SchemaIdentity(name="market_bar", version="1", fingerprint="fp"),
        transform=TransformSpec(name="canonical_bar_publisher", version="1"),
        code=CodeIdentity(commit=TEST_CODE_COMMIT),
        config=ConfigIdentity(config_sha256=TEST_CONFIG_HASH),
        dependencies=(),
        statistics=DatasetStatistics(row_count=1, byte_size=p.stat().st_size),
        coverage=CoverageWindow(event_start=datetime(2025, 1, 1, tzinfo=UTC), event_end=datetime(2025, 1, 1, 0, 1, tzinfo=UTC)),
        quality_status=QualityStatus.PASS,
        quality_summary={},
        publication=PublicationMetadata(created_at=datetime(2025, 1, 1, tzinfo=UTC)),
        supersedes_dataset_id=None,
        manifest_sha256="",
    )
    expected_id, _ = compute_dataset_id(
        identity_payload(
            dataset_type=m.dataset_type, schema=m.schema, transform=m.transform, code=m.code,
            config=m.config, dependencies=m.dependencies, files=m.files, statistics=m.statistics,
            coverage=m.coverage, quality_status=m.quality_status, quality_summary=dict(m.quality_summary),
            supersedes_dataset_id=m.supersedes_dataset_id,
        )
    )
    m2 = dataclasses.replace(m, dataset_id=expected_id)
    m2 = dataclasses.replace(m2, manifest_sha256=compute_manifest_sha256(m2))
    src = VerifiedSourceBarDataset(local_files={"bars.parquet": p}, manifest=m2,
                                   venue_id="binance", instrument_id=1, market_type="spot", interval="1m")
    with pytest.raises(ValueError, match="unsupported source schema"):
        _publish(tmp_path, [src])


def test_daily_source_timeframe_canonical_identity(tmp_path: Path) -> None:
    rows = _full_day_rows("1m")
    src = _source_dataset(tmp_path, rows=rows, relative_path="m1/bars.parquet", interval="1m", dataset_id="ds_tf")
    res_strict = _publish(tmp_path, [src], daily_source_timeframe="1m")
    assert res_strict.publish_plan.quality_status is QualityStatus.PASS


def test_whitespace_equivalent_daily_source_timeframe_identity(tmp_path: Path) -> None:
    rows = _full_day_rows("1m")

    def build(tf):
        src = _source_dataset(tmp_path, rows=rows, relative_path=f"tf_{tf.strip()}/bars.parquet",
                              interval="1m", dataset_id=f"ds_tf_{tf.strip()}")
        return _publish(tmp_path, [src], daily_source_timeframe=tf)

    res_strict = build("1m")
    res_whitespace = build(" 1m ")
    assert res_strict.publish_plan.config.config_sha256 == res_whitespace.publish_plan.config.config_sha256
