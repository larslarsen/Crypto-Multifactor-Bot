"""Focused production-contract tests for the CEX-002 hourly kline products."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
import zipfile
from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from cryptofactors.ingest import binance_usdm_klines as kl


HEADER = ",".join(kl.KLINE_FIELDS)
HOUR = kl.EXPECTED_CADENCE_MS


def _line(
    open_time: int,
    *,
    open_price: str = "100.000000000000000001",
    high: str = "110.000000000000000002",
    low: str = "90.000000000000000003",
    close: str = "105.000000000000000004",
    volume: str = "20.000000000000000005",
    close_time: int | None = None,
    quote_volume: str = "2000.000000000000000006",
    count: str = "7",
    buy_volume: str = "12.000000000000000007",
    buy_quote_volume: str = "1250.000000000000000008",
    reserved: str = "0",
) -> str:
    return ",".join(
        (
            str(open_time),
            open_price,
            high,
            low,
            close,
            volume,
            str(open_time + kl.EXPECTED_CLOSE_OFFSET_MS if close_time is None else close_time),
            quote_volume,
            count,
            buy_volume,
            buy_quote_volume,
            reserved,
        )
    )


def _key(symbol: str, period: str, family: str) -> str:
    cadence = family.split("/", 1)[0]
    return f"data/futures/um/{cadence}/klines/{symbol}/1h/{symbol}-1h-{period}.zip"


def _zip_bytes(key: str, rows: list[str], *, headed: bool = True, member: str | None = None) -> bytes:
    target = BytesIO()
    name = member or key.rsplit("/", 1)[-1][:-4] + ".csv"
    body = "\n".join(([HEADER] if headed else []) + rows) + "\n"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, body.encode())
    return target.getvalue()


def _source(
    tmp_path: Path,
    period: str,
    rows: list[str],
    *,
    symbol: str = "BTCUSDT",
    family: str = "daily/klines",
    headed: bool = True,
    payload: bytes | None = None,
) -> kl.RawKlineObject:
    key = _key(symbol, period, family)
    body = payload if payload is not None else _zip_bytes(key, rows, headed=headed)
    path = tmp_path / f"{symbol}-{period}-{family.split('/', 1)[0]}.zip"
    path.write_bytes(body)
    return kl.RawKlineObject(
        source_key=key,
        family=family,
        native_symbol=symbol,
        economic_period=period,
        path=path,
        source_sha256=hashlib.sha256(body).hexdigest(),
        byte_size=len(body),
        validation_state=kl.OUTCOME_CHECKSUM_VERIFIED,
        retrieval_time="2026-09-02T00:00:00Z",
    )


def _normalize(tmp_path: Path, sources: list[kl.RawKlineObject]) -> kl.KlineNormalizationResult:
    return kl.normalize_kline_sources(
        sources,
        tmp_path / ".bars",
        tmp_path / ".flow",
    )


def _tables(result: kl.KlineNormalizationResult):
    assert len(result.bar.partitions) == len(result.trade_flow.partitions) == 1
    return (
        pq.read_table(result.bar.partitions[0].parquet_path),
        pq.read_table(result.trade_flow.partitions[0].parquet_path),
    )


@pytest.mark.parametrize("headed", [True, False])
def test_headed_and_headerless_rows_publish_both_exact_schemas(
    tmp_path: Path,
    headed: bool,
) -> None:
    source = _source(tmp_path, "2026-07-01", [_line(1_782_864_000_000)], headed=headed)
    result = _normalize(tmp_path, [source])
    bars, flow = _tables(result)

    assert bars.schema == kl.BAR_SCHEMA
    assert flow.schema == kl.TRADE_FLOW_SCHEMA
    assert bars.column("venue").to_pylist() == ["BINANCE_USDM"]
    assert bars.column("native_symbol").to_pylist() == ["BTCUSDT"]
    assert bars.column("canonical_instrument_id").to_pylist() == [None]
    assert bars.column("reference_identity_state").to_pylist() == [
        "reference_identity_not_yet_created"
    ]
    assert "taker_sell_volume" not in bars.column_names
    assert "open" not in flow.column_names


def test_exact_values_and_four_trade_flow_derivations(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07-01", [_line(1_782_864_000_000)])
    bars, flow = _tables(_normalize(tmp_path, [source]))

    assert bars.column("open").to_pylist() == [Decimal("100.000000000000000001")]
    assert bars.column("source_reserved").to_pylist() == [0]
    assert flow.column("volume").to_pylist() == [Decimal("20.000000000000000005")]
    assert flow.column("taker_sell_volume").to_pylist() == [Decimal("7.999999999999999998")]
    assert flow.column("taker_sell_quote_volume").to_pylist() == [
        Decimal("749.999999999999999998")
    ]
    assert flow.column("volume_imbalance").to_pylist() == [Decimal("4.000000000000000009")]
    assert flow.column("quote_volume_imbalance").to_pylist() == [
        Decimal("500.000000000000000010")
    ]


@pytest.mark.parametrize(
    "row,match",
    [
        (_line(1_782_864_000_001), "hourly epoch"),
        (_line(1_782_864_000_000, close_time=1_782_867_599_998), "close"),
        (_line(1_782_864_000_000, open_price="0"), "positive"),
        (_line(1_782_864_000_000, high="99"), "high"),
        (_line(1_782_864_000_000, low="106"), "low"),
        (_line(1_782_864_000_000, volume="-1"), "negative"),
        (_line(1_782_864_000_000, count="-1"), "negative"),
        (_line(1_782_864_000_000, reserved="-1"), "negative"),
        (_line(1_782_864_000_000, volume="10", buy_volume="11"), "exceeds total"),
        (
            _line(1_782_864_000_000, quote_volume="10", buy_quote_volume="11"),
            "exceeds total",
        ),
        (_line(1_782_864_000_000, open_price="nan"), "exact decimal"),
    ],
)
def test_timestamp_decimal_and_economic_violations_fail_without_completion(
    tmp_path: Path,
    row: str,
    match: str,
) -> None:
    with pytest.raises(kl.KlineNormalizationError, match=match):
        _normalize(tmp_path, [_source(tmp_path, "2026-07-01", [row])])
    assert not list((tmp_path / ".bars" / ".complete").glob("*.json"))
    assert not list((tmp_path / ".flow" / ".complete").glob("*.json"))


@pytest.mark.parametrize(
    "family,period,open_time",
    [
        ("daily/klines", "2026-07-01", 1_782_864_000_000),
        ("monthly/klines", "2026-07", 1_782_864_000_000),
    ],
)
def test_daily_and_monthly_identity_periods_are_enforced(
    tmp_path: Path,
    family: str,
    period: str,
    open_time: int,
) -> None:
    result = _normalize(
        tmp_path,
        [_source(tmp_path, period, [_line(open_time)], family=family)],
    )
    assert result.bar.partitions[0].utc_month == "2026-07"


def test_row_outside_filename_period_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(kl.KlineNormalizationError, match="economic period"):
        _normalize(
            tmp_path,
            [_source(tmp_path, "2026-07-01", [_line(1_782_950_400_000)])],
        )


def test_daily_monthly_overlap_fails_before_publication(tmp_path: Path) -> None:
    monthly = _source(
        tmp_path,
        "2026-07",
        [_line(1_782_864_000_000)],
        family="monthly/klines",
    )
    daily = _source(tmp_path, "2026-07-01", [_line(1_782_864_000_000)])
    with pytest.raises(kl.KlineNormalizationError, match="overlaps"):
        _normalize(tmp_path, [monthly, daily])


@pytest.mark.parametrize("conflicting", [False, True])
def test_repeated_open_timestamp_is_always_rejected(
    tmp_path: Path,
    conflicting: bool,
) -> None:
    timestamp = 1_782_864_000_000
    rows = [_line(timestamp), _line(timestamp, close="106" if conflicting else "105.000000000000000004")]
    with pytest.raises(kl.KlineNormalizationError, match="duplicate"):
        _normalize(tmp_path, [_source(tmp_path, "2026-07-01", rows)])


def test_within_object_gap_is_typed_for_both_products(tmp_path: Path) -> None:
    start = 1_782_864_000_000
    result = _normalize(
        tmp_path,
        [_source(tmp_path, "2026-07-01", [_line(start), _line(start + 3 * HOUR)])],
    )
    for artifact, product in (
        (result.bar.gap_artifact, kl.BAR_PRODUCT),
        (result.trade_flow.gap_artifact, kl.TRADE_FLOW_PRODUCT),
    ):
        rows = pq.read_table(artifact.parquet_path).to_pylist()
        assert rows == [
            {
                **kl.native_identity("BTCUSDT"),
                "required_product": product,
                "utc_month": "2026-07",
                "missing_run_start_ms": start + HOUR,
                "missing_run_end_ms": start + 2 * HOUR,
                "expected_grid_count": 2,
                "gap_kind": "missing_hour_run",
                "reason": "within_object_missing_hour",
            }
        ]


def test_between_object_gap_and_partition_local_lineage(tmp_path: Path) -> None:
    first_time = 1_782_946_800_000  # 2026-07-01T23:00:00Z
    second_time = first_time + 3 * HOUR
    first = _source(tmp_path, "2026-07-01", [_line(first_time)])
    second = _source(tmp_path, "2026-07-02", [_line(second_time)])
    result = _normalize(tmp_path, [second, first])
    bars, flow = _tables(result)

    assert bars.column("raw_object_ref").to_pylist() == [0, 1]
    assert flow.column("raw_object_ref").to_pylist() == [0, 1]
    lineage = json.loads(result.bar.partitions[0].lineage_path.read_text())
    assert [item["source_key"] for item in lineage["raw_objects"]] == [
        first.source_key,
        second.source_key,
    ]
    assert lineage["raw_objects"][0]["source_sha256"] == first.source_sha256
    assert lineage["raw_objects"][0]["source_availability_state"] == "unknown_not_imputed"
    gaps = pq.read_table(result.bar.gap_artifact.parquet_path).to_pylist()
    assert gaps[0]["reason"] == "between_object_missing_hour"
    assert gaps[0]["expected_grid_count"] == 2


def test_cross_month_gap_is_split_without_market_row_invention(tmp_path: Path) -> None:
    december_time = 1_798_754_400_000  # 2026-12-31T22:00:00Z
    january_time = december_time + 4 * HOUR
    december = _source(tmp_path, "2026-12-31", [_line(december_time)])
    january = _source(tmp_path, "2027-01-01", [_line(january_time)])
    result = _normalize(tmp_path, [january, december])
    gaps = pq.read_table(result.bar.gap_artifact.parquet_path).to_pylist()

    assert [(row["utc_month"], row["expected_grid_count"]) for row in gaps] == [
        ("2026-12", 1),
        ("2027-01", 2),
    ]
    assert sum(part.row_count for part in result.bar.partitions) == 2


def test_completion_reconciles_two_separate_products(tmp_path: Path) -> None:
    start = 1_782_864_000_000
    source = _source(tmp_path, "2026-07-01", [_line(start), _line(start + HOUR)])
    result = _normalize(tmp_path, [source])

    for product_result in (result.bar, result.trade_flow):
        completion = json.loads(product_result.completion_path.read_text())
        assert completion["required_product"] == product_result.product
        assert completion["schema_sha256"] == product_result.schema_sha256
        assert completion["source_count"] == 1
        assert completion["source_bytes"] == source.byte_size
        assert completion["row_equation"] == {
            "physical_rows": 2,
            "duplicate_rows": 0,
            "overlap_rows": 0,
            "collapsed_rows": 0,
            "excluded_rows": 0,
            "product_rows": 2,
        }
        assert completion["quality_gap_artifact"]["row_count"] == 0
    assert result.bar.completion_path.parent.parent != result.trade_flow.completion_path.parent.parent


def test_byte_identical_replay_reuses_every_product_artifact(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07-01", [_line(1_782_864_000_000)])
    first = _normalize(tmp_path, [source])
    bar_bytes = first.bar.completion_path.read_bytes()
    flow_bytes = first.trade_flow.completion_path.read_bytes()
    second = _normalize(tmp_path, [source])

    assert second.bar.partitions[0].reused is True
    assert second.trade_flow.partitions[0].reused is True
    assert second.bar.completion_reused is True
    assert second.trade_flow.completion_reused is True
    assert second.bar.completion_path.read_bytes() == bar_bytes
    assert second.trade_flow.completion_path.read_bytes() == flow_bytes


def test_interruption_leaves_no_product_completion(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07-01", [_line(1_782_864_000_000)])

    def interrupt(product: str, kind: str, _stage: Path, _destination: Path) -> None:
        if product == kl.TRADE_FLOW_PRODUCT and kind == "partition":
            raise RuntimeError("injected dual-product interruption")

    with pytest.raises(RuntimeError, match="injected"):
        kl.normalize_kline_sources(
            [source],
            tmp_path / ".bars",
            tmp_path / ".flow",
            hooks=kl.PublicationHooks(before_publish=interrupt),
        )
    assert not list((tmp_path / ".bars" / ".complete").glob("*.json"))
    assert not list((tmp_path / ".flow" / ".complete").glob("*.json"))


def test_content_address_collision_with_different_bytes_fails(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07-01", [_line(1_782_864_000_000)])
    injected = False

    def collide(product: str, kind: str, _stage: Path, destination: Path) -> None:
        nonlocal injected
        if not injected and product == kl.BAR_PRODUCT and kind == "partition":
            destination.write_bytes(b"not the addressed parquet")
            injected = True

    with pytest.raises(kl.KlineNormalizationError, match="differs"):
        kl.normalize_kline_sources(
            [source],
            tmp_path / ".bars",
            tmp_path / ".flow",
            hooks=kl.PublicationHooks(before_publish=collide),
        )


@pytest.mark.parametrize("member", ["../escape.csv", "/absolute.csv", "nested/file.csv", "wrong.csv"])
def test_unsafe_zip_member_paths_are_rejected(tmp_path: Path, member: str) -> None:
    key = _key("BTCUSDT", "2026-07-01", "daily/klines")
    payload = _zip_bytes(key, [_line(1_782_864_000_000)], member=member)
    with pytest.raises(kl.KlineNormalizationError):
        _normalize(tmp_path, [_source(tmp_path, "2026-07-01", [], payload=payload)])


def test_symlink_and_multi_member_zips_are_rejected(tmp_path: Path) -> None:
    target = BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        info = zipfile.ZipInfo("BTCUSDT-1h-2026-07-01.csv")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, b"target")
    with pytest.raises(kl.KlineNormalizationError, match="regular"):
        _normalize(tmp_path, [_source(tmp_path, "2026-07-01", [], payload=target.getvalue())])

    target = BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("BTCUSDT-1h-2026-07-01.csv", _line(1_782_864_000_000))
        archive.writestr("extra.csv", "x")
    with pytest.raises(kl.KlineNormalizationError, match="exactly one"):
        _normalize(tmp_path, [_source(tmp_path, "2026-07-01", [], payload=target.getvalue())])


def test_1025th_row_exceeds_finite_parser_bound(tmp_path: Path) -> None:
    row = _line(1_782_864_000_000)
    with pytest.raises(kl.KlineNormalizationError, match="row parser bound"):
        _normalize(tmp_path, [_source(tmp_path, "2026-07-01", [row] * 1_025)])


def test_arbitrary_first_row_is_not_treated_as_a_header(tmp_path: Path) -> None:
    with pytest.raises(kl.KlineNormalizationError, match="exact integer"):
        _normalize(
            tmp_path,
            [_source(tmp_path, "2026-07-01", ["x," + ",".join(["1"] * 11)], headed=False)],
        )


@pytest.mark.parametrize("state", [kl.OUTCOME_CHECKSUM_VERIFIED, kl.OUTCOME_RETAINED])
def test_only_accepted_generation0_validation_states_pass(state: str) -> None:
    kl._require_accepted_validation_state(state)


def test_unknown_generation0_validation_state_is_rejected() -> None:
    with pytest.raises(kl.KlineNormalizationError, match="not accepted"):
        kl._require_accepted_validation_state("unknown")


def test_plan_payload_must_bind_identity_family_symbol_period_and_bytes() -> None:
    identity = _key("BTCUSDT", "2026-07-01", "daily/klines")
    payload = {
        "key": identity,
        "family": "daily/klines",
        "symbol": "BTCUSDT",
        "economic_interval": "2026-07-01",
        "listed_bytes": 123,
        "sidecar_key": f"{identity}.CHECKSUM",
    }
    assert kl._validate_plan_payload(identity, payload, 123) == (
        "daily/klines",
        "BTCUSDT",
        "2026-07-01",
    )
    for field in ("key", "family", "symbol", "economic_interval", "listed_bytes", "sidecar_key"):
        changed = dict(payload)
        changed[field] = "wrong"
        with pytest.raises(kl.KlineNormalizationError):
            kl._validate_plan_payload(identity, changed, 123)


def test_minimal_substitute_generation0_database_is_rejected(tmp_path: Path) -> None:
    state = tmp_path / "state.sqlite"
    connection = sqlite3.connect(state)
    connection.execute("CREATE TABLE substitute(value TEXT)")
    connection.commit()
    connection.close()
    content = tmp_path / "content"
    content.mkdir()

    with pytest.raises(RuntimeError):
        kl.load_generation0_kline_sources(state, content)


def test_source_checksum_and_descriptor_substitution_fail(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07-01", [_line(1_782_864_000_000)])
    substituted = replace(source, source_sha256="0" * 64)
    with pytest.raises(kl.KlineNormalizationError, match="bytes"):
        _normalize(tmp_path, [substituted])


def test_symlinked_raw_source_path_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07-01", [_line(1_782_864_000_000)])
    link = tmp_path / "source-link.zip"
    link.symlink_to(source.path)
    with pytest.raises(kl.KlineNormalizationError, match="symlink"):
        _normalize(tmp_path, [replace(source, path=link)])


@pytest.mark.parametrize("bad_roots", [("bars", ".flow"), (".same", ".same")])
def test_output_roots_must_be_hidden_and_distinct(
    tmp_path: Path,
    bad_roots: tuple[str, str],
) -> None:
    source = _source(tmp_path, "2026-07-01", [_line(1_782_864_000_000)])
    with pytest.raises(kl.KlineNormalizationError):
        kl.normalize_kline_sources(
            [source],
            tmp_path / bad_roots[0],
            tmp_path / bad_roots[1],
        )
