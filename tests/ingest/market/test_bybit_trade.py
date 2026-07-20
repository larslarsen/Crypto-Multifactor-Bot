"""Focused BYB-001 regressions against the Bybit trade-archive normalizer.

Covers: audited-shape linear and inverse rows; exact timestamps with six, fewer,
and invalid excess fractional digits; descending/mixed-order archives preserving
source order with ordering diagnostics and correct min/max coverage; strict
header/width/symbol/side/tick/number validation; linear base-size versus inverse
contract-size semantics (no invented inverse volume); bounded gzip/row limits and
bad gzip; empty/header-only input; duplicate/conflicting trade IDs within and
across objects with no hidden row deletion; source row/raw-object lineage and
deterministic config/schema identities; safe paths, output verification, and full
MAN-001 catalog publication; explicit no-network behavior.

Transform: BYBIT_TRADE_TRANSFORM_VERSION = "1"
Schema:   BYBIT_TRADE_SCHEMA_VERSION   = "1"
"""

from __future__ import annotations

import gzip
import io
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import (
    DatasetStoreConfig,
    DependencyKind,
    RowCountPolicy,
)
from cryptofactors.catalog.dataset.outputs import verify_outputs
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations
from cryptofactors.contracts import RawObject
from cryptofactors.ingest.bybit import (
    BYBIT_TRADE_SCHEMA_VERSION,
    BYBIT_TRADE_TRANSFORM_VERSION,
    BybitTradeNormalizeResult,
    normalize_bybit_trades,
)

TEST_CODE_COMMIT = "0" * 40
TEST_CONFIG_HASH = "a" * 64

_AUDITED_HEADER = (
    "timestamp,symbol,side,size,price,tickDirection,trdMatchID,"
    "grossValue,homeNotional,foreignNotional"
)


# helpers -------------------------------------------------------------------


def _ro(tmp_path: Path, name: str, content: bytes) -> RawObject:
    p = tmp_path / name
    p.write_bytes(content)
    return RawObject(
        raw_object_id=name,
        source_id="bybit",
        sha256="deadbeef",
        bytes=len(content),
        storage_path=p,
        acquired_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def _gz(rows: list[str]) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(("\n".join(rows) + "\n").encode("utf-8"))
    return buf.getvalue()


def _row(
    ts: str = "1585180700.0647",
    symbol: str = "BTCUSDT",
    side: str = "Buy",
    size: str = "0.042",
    price: str = "6698.5",
    tick: str = "PlusTick",
    mid: str | None = None,
    gross: str = "28133700000.0",
    home: str = "0.042",
    foreign: str = "281.337",
) -> str:
    # Deterministic, unique-per-row trade ID so default fixtures never collide.
    if mid is None:
        mid = f"id-{ts.replace('.', '')}"
    return f"{ts},{symbol},{side},{size},{price},{tick},{mid},{gross},{home},{foreign}"


def _normalize(tmp_path: Path, content: bytes, *, contract_style: str, source_symbol: str,
               instrument_id: str, raw_name: str = "raw_1.csv.gz", out_sub: str = "out",
               max_rows: int = 5_000_000,
               max_decompressed_bytes: int = 209_715_200) -> BybitTradeNormalizeResult:
    raw = _ro(tmp_path, raw_name, content)
    out = tmp_path / out_sub
    return normalize_bybit_trades(
        [raw],
        contract_style=contract_style,
        source_symbol=source_symbol,
        venue_id="bybit",
        instrument_id=instrument_id,
        output_dir=out,
        code_commit=TEST_CODE_COMMIT,
        config_sha256=TEST_CONFIG_HASH,
        max_rows=max_rows,
        max_decompressed_bytes=max_decompressed_bytes,
    )


def _codes(res: BybitTradeNormalizeResult) -> list[tuple[str, str]]:
    return [(i.code, i.severity.value) for i in res.issues]


def _trade_rows(res: BybitTradeNormalizeResult) -> "pa.Table":
    return pq.read_table(res.trade_paths[0])


# required Jr cases ----------------------------------------------------------


def test_audited_linear_shape_pass(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(), _row(ts="1585180700.02")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="BTCUSDT-PERP")
    assert res.publish_plan.quality_status.value == "PASS"
    part = res.publish_plan.output_specs[0].partition
    assert part["market_type"] == "usdm"
    assert part["size_unit"] == "base_asset"
    assert part["schema_variant"] == "linear_base_size"
    tbl = _trade_rows(res)
    assert tbl.num_rows == 2
    assert tbl.column("side")[0].as_py() == "buy"
    assert tbl.column("event_time")[0].as_py() == 1585180700064700
    assert tbl.column("source_timestamp")[0].as_py() == "1585180700.0647"
    assert tbl.column("source_timestamp_unit")[0].as_py() == "decimal_seconds"
    assert tbl.column("size")[0].as_py() == Decimal("0.042")


def test_audited_inverse_shape_pass(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(symbol="BTCUSD", size="11668", price="8319.5",
                                         gross="140248813.0", home="11668", foreign="1.40248813")])
    res = _normalize(tmp_path, content, contract_style="inverse",
                     source_symbol="BTCUSD", instrument_id="BTCUSD-PERP")
    assert res.publish_plan.quality_status.value == "PASS"
    part = res.publish_plan.output_specs[0].partition
    assert part["market_type"] == "coinm"
    assert part["size_unit"] == "contracts"
    assert part["schema_variant"] == "inverse_contract_size"
    # inverse size preserved as contract quantity; no base/quote volume invented
    tbl = _trade_rows(res)
    assert tbl.column("size")[0].as_py() == Decimal("11668")
    assert tbl.column("home_notional")[0].as_py() == Decimal("11668")
    assert tbl.column("foreign_notional")[0].as_py() == Decimal("1.40248813")


def test_timestamp_six_digits(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(ts="1585180700.064700")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "PASS"
    assert _trade_rows(res).column("event_time")[0].as_py() == 1585180700064700


def test_timestamp_fewer_digits(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(ts="1585180700.02")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "PASS"
    assert _trade_rows(res).column("event_time")[0].as_py() == 1585180700020000


def test_timestamp_invalid_excess_fractional_rejected(tmp_path: Path) -> None:
    # nonzero sub-microsecond digits -> invalid, not rounded-away
    content = _gz([_AUDITED_HEADER, _row(ts="1585180700.0647000000001")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_invalid_timestamp", "error") in _codes(res)


def test_timestamp_tiny_submicro_rejected(tmp_path: Path) -> None:
    # discarded fractional width exceeds coefficient length -> still invalid
    content = _gz([_AUDITED_HEADER, _row(ts="0.0000000000001")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_invalid_timestamp", "error") in _codes(res)


def test_descending_order_preserved_with_diagnostic(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(ts="1585180700.09"),
                   _row(ts="1585180700.02"), _row(ts="1585180700.01")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "PASS"
    summary = res.publish_plan.quality_summary
    assert summary["ordering_per_object"]["raw_1.csv.gz"] == "descending"
    # source row order preserved (descending timestamps in output)
    tbl = _trade_rows(res)
    ev = [tbl.column("event_time")[i].as_py() for i in range(tbl.num_rows)]
    assert ev == sorted(ev, reverse=True)
    # coverage uses observed min/max independent of row order
    assert res.publish_plan.coverage.event_start == datetime.fromtimestamp(
        1585180700.01, tz=timezone.utc)
    assert res.publish_plan.coverage.event_end == datetime.fromtimestamp(
        1585180700.09, tz=timezone.utc)


def test_mixed_order_preserved_with_diagnostic(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(ts="1585180700.05"),
                   _row(ts="1585180700.09"), _row(ts="1585180700.02")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    # Direction reversal is a warning, not a rejection (row order is not economic identity).
    assert res.publish_plan.quality_status.value == "PASS_WITH_WARNINGS"
    assert ("bybit_trade_nonmonotonic_timestamp", "warning") in _codes(res)
    summary = res.publish_plan.quality_summary
    assert summary["ordering_per_object"]["raw_1.csv.gz"] == "mixed"
    tbl = _trade_rows(res)
    ev = [tbl.column("event_time")[i].as_py() for i in range(tbl.num_rows)]
    assert ev == [1585180700050000, 1585180700090000, 1585180700020000]


def test_header_mismatch_rejected(tmp_path: Path) -> None:
    bad_header = "timestamp,symbol,side,size,price,tickDirection,trdMatchID,grossValue,homeNotional"
    content = _gz([bad_header, _row()])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_archive_header_mismatch", "error") in _codes(res)


def test_row_width_rejected(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, "1585180700.0647,BTCUSDT,Buy,0.042,6698.5,PlusTick,mid,1,1"])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_row_width", "error") in _codes(res)


def test_symbol_mismatch_rejected(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(symbol="ETHUSDT")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_symbol_mismatch", "error") in _codes(res)


def test_invalid_side_rejected(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(side="Long")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_parse_failure", "error") in _codes(res)


def test_invalid_tick_direction_rejected(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(tick="UpTick")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_parse_failure", "error") in _codes(res)


def test_nonpositive_size_rejected(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(size="0")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_parse_failure", "error") in _codes(res)


def test_empty_observations_rejected(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_empty_observations", "error") in _codes(res)


def test_bad_gzip_rejected(tmp_path: Path) -> None:
    content = b"this is not gzip data at all"
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_archive_bad_gzip", "error") in _codes(res)


def test_strict_malformed_quote_rejected(tmp_path: Path) -> None:
    # unterminated quoted field must fail closed under strict CSV
    content = _gz([_AUDITED_HEADER,
                   '1585180700.0647,BTCUSDT,Buy,"0.042,6698.5,PlusTick,mid,1,1,1'])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_parse_failure", "error") in _codes(res)


def test_overscale_decimal_rejected(tmp_path: Path) -> None:
    # 39-digit size exceeds decimal128(38,18); must fail closed
    content = _gz([_AUDITED_HEADER, _row(size="1" * 39)])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_parse_failure", "error") in _codes(res)


def test_duplicate_id_within_object_rejected_no_row_deletion(tmp_path: Path) -> None:
    mid = "dup-11111111111111111111111111111111"
    content = _gz([_AUDITED_HEADER, _row(mid=mid), _row(mid=mid)])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_duplicate_id", "error") in _codes(res)
    # both rows preserved; no silent dedupe
    assert _trade_rows(res).num_rows == 2


def test_conflicting_duplicate_id_rejected_no_row_deletion(tmp_path: Path) -> None:
    mid = "cf-11111111111111111111111111111111"
    content = _gz([_AUDITED_HEADER, _row(mid=mid), _row(mid=mid, price="7000.0")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_trade_conflicting_duplicate_id", "error") in _codes(res)
    assert _trade_rows(res).num_rows == 2


def test_duplicate_id_across_objects(tmp_path: Path) -> None:
    mid = "xs-11111111111111111111111111111111"
    # Identical payload (same trade ID and content) across two raw objects.
    same = _row(mid=mid, ts="1585180700.01")
    c1 = _gz([_AUDITED_HEADER, same])
    c2 = _gz([_AUDITED_HEADER, same])
    raw1 = _ro(tmp_path, "a.csv.gz", c1)
    raw2 = _ro(tmp_path, "b.csv.gz", c2)
    out = tmp_path / "out"
    res = normalize_bybit_trades(
        [raw1, raw2], contract_style="linear", source_symbol="BTCUSDT",
        venue_id="bybit", instrument_id="X", output_dir=out,
        code_commit=TEST_CODE_COMMIT, config_sha256=TEST_CONFIG_HASH,
    )
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert any(i.code == "bybit_trade_duplicate_id" for i in res.issues)
    # Rows are preserved per object; no silent cross-object merge/dedupe.
    assert len(res.trade_paths) == 2
    assert _trade_rows(res).num_rows == 1  # a.csv.gz only


def test_source_row_lineage_preserved(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(ts="1585180700.09"),
                   _row(ts="1585180700.02"), _row(ts="1585180700.01")])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    tbl = _trade_rows(res)
    assert tbl.column("source_row_number").to_pylist() == [1, 2, 3]
    assert set(tbl.column("raw_object_id").to_pylist()) == {"raw_1.csv.gz"}


def test_deterministic_config_and_schema_identity(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row()])
    r1 = _normalize(tmp_path, content, contract_style="linear",
                    source_symbol="BTCUSDT", instrument_id="X", out_sub="o1")
    r2 = _normalize(tmp_path, content, contract_style="linear",
                    source_symbol="BTCUSDT", instrument_id="X", out_sub="o2")
    assert r1.publish_plan.config.config_sha256 == r2.publish_plan.config.config_sha256
    assert r1.publish_plan.schema.fingerprint == r2.publish_plan.schema.fingerprint
    assert r1.publish_plan.schema.version == BYBIT_TRADE_SCHEMA_VERSION == "1"
    assert r1.publish_plan.transform.version == BYBIT_TRADE_TRANSFORM_VERSION == "1"
    assert r1.publish_plan.code.commit == TEST_CODE_COMMIT


def test_storage_root_independent_quality_identity(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row(), _row(ts="1585180700.02")])
    rA = _normalize(tmp_path, content, contract_style="linear",
                    source_symbol="BTCUSDT", instrument_id="X", out_sub="A")
    rB = _normalize(Path(tempfile.mkdtemp()), content, contract_style="linear",
                    source_symbol="BTCUSDT", instrument_id="X", out_sub="B")
    qA = [s for s in rA.publish_plan.output_specs if s.relative_path.endswith("quality.parquet")][0]
    qB = [s for s in rB.publish_plan.output_specs if s.relative_path.endswith("quality.parquet")][0]
    assert qA.sha256 == qB.sha256


def test_safe_output_paths(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row()])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    rels = sorted(res.publish_plan.output_sources)
    assert all(p.startswith("bybit/usdm/trades/raw_raw_1.csv.gz/") for p in rels)
    assert any(p.endswith("trades.parquet") for p in rels)
    assert any(p.endswith("quality.parquet") for p in rels)


def test_verify_outputs_passes(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row()])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    plan = res.publish_plan
    verified = verify_outputs(
        sources=dict(plan.output_sources),
        specs=list(plan.output_specs),
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters=dict(plan.row_counters),
    )
    assert len(verified) == len(plan.output_specs)


def test_full_man001_catalog_publish(tmp_path: Path) -> None:
    content = _gz([_AUDITED_HEADER, _row()])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="BTCUSDT-PERP")
    plan = res.publish_plan

    db = tmp_path / "control.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    cat = SqliteDatasetCatalog(db)
    cat._conn.execute(
        "INSERT OR IGNORE INTO source (source_id, source_type, official_url, terms_class, config_json, created_at) VALUES (?, 'external', NULL, NULL, '{}', ?)",
        ("bybit", datetime.now(timezone.utc).isoformat()),
    )
    cat._conn.execute(
        "INSERT OR IGNORE INTO raw_object (raw_object_id, source_id, sha256, byte_size, storage_uri, original_name, request_json, response_metadata_json, source_checksum, acquired_at, event_start, event_end, status) VALUES (?, ?, ?, ?, ?, NULL, '{}', '{}', NULL, ?, NULL, NULL, 'ACQUIRED')",
        ("raw_1.csv.gz", "bybit", "deadbeef", 0, "raw/sha256/de/adbeef",
         datetime.now(timezone.utc).isoformat()),
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
    assert plan.quality_status.value == "PASS"
    assert plan.dependencies[0].kind is DependencyKind.RAW_OBJECT
    assert plan.dependencies[0].role == "bybit_trade_archive"


def test_no_network_required(tmp_path: Path) -> None:
    # The normalizer performs no discovery/HTTP/auth; a purely local file runs
    # to completion offline with no network access.
    content = _gz([_AUDITED_HEADER, _row()])
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X")
    assert res.publish_plan.quality_status.value == "PASS"
    assert res.publish_plan.quality_summary["provider_role"] == "CONDITIONAL - CROSSCHECK"


def test_row_limit_exceeded_rejected(tmp_path: Path) -> None:
    rows = [_AUDITED_HEADER] + [_row(ts=f"1585180700.0{i:06d}") for i in range(5)]
    content = _gz(rows)
    res = _normalize(tmp_path, content, contract_style="linear",
                     source_symbol="BTCUSDT", instrument_id="X", max_rows=3)
    assert res.publish_plan.quality_status.value == "REJECTED"
    assert ("bybit_archive_limit_exceeded", "error") in _codes(res)
