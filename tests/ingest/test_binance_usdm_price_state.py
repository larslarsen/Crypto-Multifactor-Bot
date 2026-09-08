"""Focused contract tests for the two CEX-002 hourly price-state products."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import weakref
import zipfile
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, localcontext
from io import BytesIO
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from cryptofactors.ingest import binance_usdm_price_state as ps


HOUR = ps.EXPECTED_CADENCE_MS
JULY = 1_782_864_000_000
HEADER = ",".join(ps.FIELDS)


def _line(
    open_time: int,
    *,
    open_value: str = "100.000000000000000001",
    high: str = "110.000000000000000002",
    low: str = "1.000000000000000003",
    close: str = "105.000000000000000004",
    volume: str = "0",
    close_time: int | None = None,
    quote_volume: str = "0",
    count: str = "0",
    buy_volume: str = "0",
    buy_quote_volume: str = "0",
    reserved: str = "0",
) -> str:
    return ",".join(
        (
            str(open_time),
            open_value,
            high,
            low,
            close,
            volume,
            str(open_time + ps.EXPECTED_CLOSE_OFFSET_MS if close_time is None else close_time),
            quote_volume,
            count,
            buy_volume,
            buy_quote_volume,
            reserved,
        )
    )


def _premium_line(open_time: int, close: str = "-0.000100000000000001") -> str:
    return _line(
        open_time,
        open_value="-0.000200000000000002",
        high="0",
        low="-0.000300000000000003",
        close=close,
    )


def _family(kind: str, period: str) -> str:
    return ps.FAMILY_BY_KIND_PERIOD[(kind, "daily" if len(period) == 10 else "monthly")]


def _key(kind: str, symbol: str, period: str) -> str:
    family = _family(kind, period)
    archive = family.split("/", 1)[1]
    cadence = family.split("/", 1)[0]
    return f"data/futures/um/{cadence}/{archive}/{symbol}/1h/{symbol}-1h-{period}.zip"


def _zip_bytes(
    key: str,
    rows: list[str],
    *,
    headed: bool = True,
    member: str | None = None,
    second_member: bool = False,
) -> bytes:
    target = BytesIO()
    name = member or key.rsplit("/", 1)[-1][:-4] + ".csv"
    body = "\n".join(([HEADER] if headed else []) + rows) + "\n"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, body.encode())
        if second_member:
            archive.writestr("extra.csv", b"x")
    return target.getvalue()


def _source(
    tmp_path: Path,
    kind: str,
    period: str,
    rows: list[str],
    *,
    symbol: str = "BTCUSDT",
    headed: bool = True,
    payload: bytes | None = None,
    suffix: str = "",
    state: str = ps.OUTCOME_CHECKSUM_VERIFIED,
) -> ps.RawPriceStateObject:
    key = _key(kind, symbol, period)
    body = payload if payload is not None else _zip_bytes(key, rows, headed=headed)
    path = tmp_path / f"{symbol}-{kind}-{period}{suffix}.zip"
    path.write_bytes(body)
    return ps.RawPriceStateObject(
        source_key=key,
        family=_family(kind, period),
        kind=kind,
        native_symbol=symbol,
        economic_period=period,
        path=path,
        source_sha256=hashlib.sha256(body).hexdigest(),
        byte_size=len(body),
        validation_state=state,
        retrieval_time="2026-09-08T00:00:00Z",
    )


def _triplet(
    tmp_path: Path,
    *,
    period: str = "2026-07",
    headed: bool = True,
    mark_rows: list[str] | None = None,
    index_rows: list[str] | None = None,
    premium_rows: list[str] | None = None,
) -> list[ps.RawPriceStateObject]:
    return [
        _source(tmp_path, ps.PREMIUM, period, premium_rows or [_premium_line(JULY)], headed=headed),
        _source(tmp_path, ps.MARK, period, mark_rows or [_line(JULY, close="2")], headed=headed),
        _source(tmp_path, ps.INDEX, period, index_rows or [_line(JULY, close="3")], headed=headed),
    ]


def _normalize(
    tmp_path: Path,
    sources: list[ps.RawPriceStateObject],
    *,
    hooks: ps.PublicationHooks = ps.PublicationHooks(),
    report: dict[str, object] | None = None,
    sizing: dict[str, object] | None = None,
) -> ps.PriceStateNormalizationResult:
    return ps.normalize_price_state_sources(
        sources,
        tmp_path / ".price-state",
        hooks=hooks,
        report=report,
        sizing=sizing,
    )


def _tables(result: ps.PriceStateNormalizationResult):
    assert len(result.indicative.partitions) == len(result.basis.partitions) == 1
    return (
        pq.read_table(result.indicative.partitions[0].parquet_path),
        pq.read_table(result.basis.partitions[0].parquet_path),
    )


def _completion(result: ps.ProductResult) -> dict[str, object]:
    return json.loads(result.completion_path.read_text())


def _sizing() -> dict[str, object]:
    rows = []
    for product in ps.PRODUCTS:
        rows.append({"required_product": product, **ps.ACCEPTED_PROJECTIONS[product]})
    return {
        "authority": {"bindings": {"report_sha256": ps.REPORT_SHA256}},
        "code_identity": {
            "policy_identity": ps.SIZING_POLICY_IDENTITY,
            "writer_identity": ps.writer_identity(),
        },
        "projections": {
            "final_product_schemas": {
                product: ps._schema_contract(ps.SCHEMAS[product]) for product in ps.PRODUCTS
            },
            "required_products": rows,
        },
    }


def _report() -> dict[str, object]:
    return {
        "product_matrix": [
            {
                "product": product,
                "universe_coverage_gaps": [],
                "typed_gap_symbols": [],
                "coverage_gap_kinds": [],
                "accepted_universe_object_count": 1,
                "accepted_universe_listed_bytes": 1,
            }
            for product in ps.PRODUCTS
        ]
    }


def test_frozen_22_and_33_column_schemas_are_exact() -> None:
    assert len(ps.INDICATIVE_SCHEMA) == 22
    assert len(ps.BASIS_SCHEMA) == 33
    assert ps.INDICATIVE_SCHEMA.names == [
        "raw_object_ref", "source_row_ordinal", "venue_symbol", "open_time", "close_time",
        "premium_open", "premium_high", "premium_low", "premium_close", "premium_volume",
        "premium_quote_volume", "premium_count", "premium_taker_buy_volume",
        "premium_taker_buy_quote_volume", "source_reserved", "venue", "native_symbol",
        "canonical_instrument_id", "canonical_instrument_version_id", "reference_identity_state",
        "indicative_funding_rate", "indicative_rate_status",
    ]
    assert ps.BASIS_SCHEMA.names[-8:] == [
        "venue", "native_symbol", "canonical_instrument_id", "canonical_instrument_version_id",
        "reference_identity_state", "absolute_basis", "relative_basis", "basis_join_status",
    ]


@pytest.mark.parametrize("headed", [True, False])
@pytest.mark.parametrize("period", ["2026-07", "2026-07-01"])
def test_headed_headerless_monthly_daily_publish_both_products(
    tmp_path: Path, headed: bool, period: str
) -> None:
    indicative, basis = _tables(_normalize(tmp_path, _triplet(tmp_path, period=period, headed=headed)))
    assert indicative.schema == ps.INDICATIVE_SCHEMA
    assert basis.schema == ps.BASIS_SCHEMA
    assert indicative.column("venue").to_pylist() == ["BINANCE_USDM"]
    assert basis.column("reference_identity_state").to_pylist() == ["reference_identity_not_yet_created"]


def test_signed_and_zero_premium_are_preserved_with_unavailable_rate(tmp_path: Path) -> None:
    rows = [_premium_line(JULY), _premium_line(JULY + HOUR, close="0")]
    mark = [_line(JULY, close="2"), _line(JULY + HOUR, close="2")]
    index = [_line(JULY, close="3"), _line(JULY + HOUR, close="3")]
    result = _normalize(tmp_path, _triplet(tmp_path, premium_rows=rows, mark_rows=mark, index_rows=index))
    indicative = pq.read_table(result.indicative.partitions[0].parquet_path)
    assert indicative.column("premium_close").to_pylist() == [
        Decimal("-0.000100000000000001"), Decimal("0E-18")
    ]
    assert indicative.column("indicative_funding_rate").to_pylist() == [None, None]
    assert indicative.column("indicative_rate_status").to_pylist() == [ps.INDICATIVE_UNAVAILABLE] * 2
    assert result.premium_zip_reads == 1


def test_exact_signed_basis_and_negative_floor_are_context_independent(tmp_path: Path) -> None:
    with localcontext() as context:
        context.prec = 3
        _indicative, basis = _tables(_normalize(tmp_path, _triplet(tmp_path)))
    assert basis.column("absolute_basis").to_pylist() == [Decimal("-1.000000000000000000")]
    assert basis.column("relative_basis").to_pylist() == [Decimal("-0.333333333333333334")]
    assert basis.column("basis_join_status").to_pylist() == [ps.BASIS_JOIN_STATUS]


def test_join_uses_exact_times_and_preserves_differing_source_ordinals(tmp_path: Path) -> None:
    mark = [_line(JULY + 2 * HOUR, close="2")]
    index = [_line(JULY, close="3"), _line(JULY + 2 * HOUR, close="3")]
    premium = [_premium_line(JULY), _premium_line(JULY + HOUR), _premium_line(JULY + 2 * HOUR)]
    result = _normalize(tmp_path, _triplet(tmp_path, mark_rows=mark, index_rows=index, premium_rows=premium))
    lineage = json.loads(result.basis.partitions[0].lineage_path.read_text())
    joined = lineage["joined_source_runs"][0]
    assert joined["row_count"] == 1
    assert joined["mark_source_row_ordinal_start"] == 0
    assert joined["index_source_row_ordinal_start"] == 1
    assert joined["premium_source_row_ordinal_start"] == 2
    assert result.basis.unjoinable_source_rows == 3


def test_nonmatching_and_wholly_unjoinable_partitions_publish_durable_gaps(tmp_path: Path) -> None:
    sources = _triplet(tmp_path)
    sources.append(_source(tmp_path, ps.INDEX, "2026-08", [_line(JULY + 31 * 24 * HOUR)], suffix="-only"))
    result = _normalize(tmp_path, sources)
    assert len(result.basis.partitions) == 1
    assert any(gap.utc_month == "2026-08" for gap in result.basis.gap_artifacts)
    gap = next(gap for gap in result.basis.gap_artifacts if gap.utc_month == "2026-08")
    lineage = json.loads(gap.lineage_path.read_text())
    assert gap.unjoinable_source_rows == 1
    assert lineage["unjoinable_observations"][0]["missing_join_families"] == [ps.PREMIUM, ps.MARK]
    assert not list((tmp_path / ".price-state" / ps.BASIS_PRODUCT / ".partitions" / "BTCUSDT" / "2026-08").glob("*.parquet"))


def test_missing_hour_runs_are_typed_without_fill(tmp_path: Path) -> None:
    moments = [JULY, JULY + 2 * HOUR]
    result = _normalize(
        tmp_path,
        _triplet(
            tmp_path,
            mark_rows=[_line(moment, close="2") for moment in moments],
            index_rows=[_line(moment, close="3") for moment in moments],
            premium_rows=[_premium_line(moment) for moment in moments],
        ),
    )
    gap = result.indicative.gap_artifacts[0]
    table = pq.read_table(gap.parquet_path)
    assert table.column("missing_run_start_ms").to_pylist() == [JULY + HOUR]
    assert table.column("expected_grid_count").to_pylist() == [1]
    assert result.indicative.product_rows == 2


def test_identical_duplicates_collapse_and_conflicts_fail(tmp_path: Path) -> None:
    duplicate = _premium_line(JULY)
    sources = _triplet(tmp_path, premium_rows=[duplicate, duplicate])
    result = _normalize(tmp_path, sources)
    lineage = json.loads(result.indicative.partitions[0].lineage_path.read_text())
    assert result.indicative.physical_source_rows == 2
    assert result.indicative.collapsed_identical_rows == 1
    assert lineage["collapsed_identical_source_rows"][0]["collapsed_source_row_ordinal"] == 1
    other = tmp_path / "other"
    other.mkdir()
    conflicting = _triplet(other, premium_rows=[duplicate, _premium_line(JULY, close="0")])
    with pytest.raises(ps.PriceStateNormalizationError, match="conflicting duplicate"):
        _normalize(other, conflicting)


def test_mark_and_index_reserved_must_agree(tmp_path: Path) -> None:
    sources = _triplet(tmp_path, mark_rows=[_line(JULY, close="2", reserved="0")], index_rows=[_line(JULY, close="3", reserved="1")])
    with pytest.raises(ps.PriceStateNormalizationError, match="source_reserved"):
        _normalize(tmp_path, sources)


@pytest.mark.parametrize("kind", [ps.MARK, ps.INDEX])
def test_nonpositive_mark_or_index_prices_fail(kind: str, tmp_path: Path) -> None:
    sources = _triplet(tmp_path)
    bad = _source(tmp_path, kind, "2026-07", [_line(JULY, open_value="0")], suffix="-bad")
    sources[[source.kind for source in sources].index(kind)] = bad
    with pytest.raises(ps.PriceStateNormalizationError, match="positive"):
        _normalize(tmp_path, sources)


@pytest.mark.parametrize(
    "row,match",
    [
        (_line(JULY, close_time=JULY + HOUR), "close_time"),
        (_line(JULY + 1, close="2"), "hourly"),
        (_line(JULY, close="not-decimal"), "exact scale-18 decimal"),
        (_line(JULY, count="1.0"), "exact integer"),
        (_line(JULY, high="1", low="3", open_value="2", close="2"), "high violates"),
        (",".join(["1"] * 11), "width"),
    ],
)
def test_strict_width_time_integer_decimal_and_ohlc_validation(
    tmp_path: Path, row: str, match: str
) -> None:
    sources = _triplet(tmp_path)
    sources[1] = _source(tmp_path, ps.MARK, "2026-07", [row], suffix="-bad")
    with pytest.raises(ps.PriceStateNormalizationError, match=match):
        _normalize(tmp_path, sources)


def test_arbitrary_first_row_is_not_treated_as_header(tmp_path: Path) -> None:
    sources = _triplet(tmp_path)
    sources[0] = _source(tmp_path, ps.PREMIUM, "2026-07", ["x,y,z"], headed=False, suffix="-bad")
    with pytest.raises(ps.PriceStateNormalizationError, match="width"):
        _normalize(tmp_path, sources)


@pytest.mark.parametrize("member", ["../escape.csv", "/absolute.csv", "nested/file.csv", "wrong.csv"])
def test_unsafe_zip_member_paths_are_rejected(tmp_path: Path, member: str) -> None:
    key = _key(ps.PREMIUM, "BTCUSDT", "2026-07")
    payload = _zip_bytes(key, [_premium_line(JULY)], member=member)
    sources = _triplet(tmp_path)
    sources[0] = _source(tmp_path, ps.PREMIUM, "2026-07", [], payload=payload, suffix="-unsafe")
    with pytest.raises(ps.PriceStateNormalizationError):
        _normalize(tmp_path, sources)


def test_symlink_and_multi_member_sources_are_rejected(tmp_path: Path) -> None:
    sources = _triplet(tmp_path)
    key = _key(ps.PREMIUM, "BTCUSDT", "2026-07")
    payload = _zip_bytes(key, [_premium_line(JULY)], second_member=True)
    sources[0] = _source(tmp_path, ps.PREMIUM, "2026-07", [], payload=payload, suffix="-multi")
    with pytest.raises(ps.PriceStateNormalizationError, match="exactly one"):
        _normalize(tmp_path, sources)

    ordinary = _triplet(tmp_path)
    link = tmp_path / "linked.zip"
    link.symlink_to(ordinary[0].path)
    ordinary[0] = replace(ordinary[0], path=link)
    with pytest.raises(ps.PriceStateNormalizationError, match="symlink"):
        _normalize(tmp_path, ordinary)


def test_crc_corruption_and_raw_digest_substitution_fail(tmp_path: Path) -> None:
    key = _key(ps.PREMIUM, "BTCUSDT", "2026-07")
    marker = str(JULY).encode()
    target = BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(key.rsplit("/", 1)[-1][:-4] + ".csv", marker + b",-0.1,0,-0.2,-0.1,0," + str(JULY + ps.EXPECTED_CLOSE_OFFSET_MS).encode() + b",0,0,0,0,0\n")
    corrupted = bytearray(target.getvalue())
    corrupted[corrupted.index(marker)] ^= 1
    sources = _triplet(tmp_path)
    sources[0] = _source(tmp_path, ps.PREMIUM, "2026-07", [], payload=bytes(corrupted), suffix="-crc")
    with pytest.raises(ps.PriceStateNormalizationError):
        _normalize(tmp_path, sources)

    sources = _triplet(tmp_path)
    sources[0] = replace(sources[0], source_sha256="0" * 64)
    with pytest.raises(ps.PriceStateNormalizationError, match="bytes"):
        _normalize(tmp_path, sources)


def test_finite_row_bound_is_enforced(tmp_path: Path) -> None:
    rows = [_premium_line(JULY)] * (ps.MAX_ROWS_PER_OBJECT + 1)
    sources = _triplet(tmp_path)
    sources[0] = _source(tmp_path, ps.PREMIUM, "2026-07", rows, suffix="-large")
    with pytest.raises(ps.PriceStateNormalizationError, match="row parser bound"):
        _normalize(tmp_path, sources)


def test_identity_family_symbol_period_and_daily_monthly_overlap_fail(tmp_path: Path) -> None:
    source = _triplet(tmp_path)[0]
    with pytest.raises(ps.PriceStateNormalizationError, match="descriptor conflicts"):
        ps._preflight_sources([replace(source, native_symbol="ETHUSDT")])
    daily = _source(tmp_path, ps.PREMIUM, "2026-07-01", [_premium_line(JULY)], suffix="-daily")
    with pytest.raises(ps.PriceStateNormalizationError, match="overlap"):
        ps._preflight_sources([source, daily])


def test_source_period_ownership_is_enforced(tmp_path: Path) -> None:
    august = JULY + 31 * 24 * HOUR
    sources = _triplet(tmp_path)
    sources[0] = _source(tmp_path, ps.PREMIUM, "2026-07", [_premium_line(august)], suffix="-wrong-period")
    with pytest.raises(ps.PriceStateNormalizationError, match="outside"):
        _normalize(tmp_path, sources)


def test_only_accepted_validation_states_pass() -> None:
    ps._require_accepted_validation_state(ps.OUTCOME_CHECKSUM_VERIFIED)
    ps._require_accepted_validation_state(ps.OUTCOME_RETAINED)
    with pytest.raises(ps.PriceStateNormalizationError, match="not accepted"):
        ps._require_accepted_validation_state("unknown")


def test_plan_envelope_and_nested_payload_bind_every_identity_field() -> None:
    identity = _key(ps.MARK, "BTCUSDT", "2026-07")
    payload = {
        "key": identity,
        "family": "monthly/markPriceKlines",
        "symbol": "BTCUSDT",
        "interval": "1h",
        "economic_interval": "2026-07",
        "listed_bytes": 123,
        "sidecar_key": f"{identity}.CHECKSUM",
    }
    envelope = {"provider": ps.PROVIDER_BINANCE, "identity": identity, "kind": ps.KIND_BINANCE, "payload": payload}
    assert ps._validate_plan_envelope(identity, envelope, ps.KIND_BINANCE) == payload
    assert ps._validate_plan_payload(identity, payload, 123) == ("monthly/markPriceKlines", ps.MARK, "BTCUSDT", "2026-07")
    for field in ("key", "family", "symbol", "interval", "economic_interval", "listed_bytes", "sidecar_key"):
        changed = dict(payload)
        changed[field] = "wrong"
        with pytest.raises(ps.PriceStateNormalizationError):
            ps._validate_plan_payload(identity, changed, 123)
    for field in ("provider", "identity", "kind", "payload"):
        changed = dict(envelope)
        changed[field] = "wrong"
        with pytest.raises(ps.PriceStateNormalizationError):
            ps._validate_plan_envelope(identity, changed, ps.KIND_BINANCE)


def test_sidecar_statement_binds_raw_digest_and_zip_basename() -> None:
    digest = "a" * 64
    ps._parse_sidecar_statement(f"{digest}  BTCUSDT-1h-2026-07.zip\n".encode(), content_sha256=digest, zip_basename="BTCUSDT-1h-2026-07.zip")
    with pytest.raises(ps.PriceStateNormalizationError, match="checksum"):
        ps._parse_sidecar_statement(f"{'b' * 64}  BTCUSDT-1h-2026-07.zip\n".encode(), content_sha256=digest, zip_basename="BTCUSDT-1h-2026-07.zip")
    with pytest.raises(ps.PriceStateNormalizationError, match="basename"):
        ps._parse_sidecar_statement(f"{digest}  ETHUSDT-1h-2026-07.zip\n".encode(), content_sha256=digest, zip_basename="BTCUSDT-1h-2026-07.zip")


def test_physical_sidecar_path_size_hash_and_statement_are_all_required(tmp_path: Path) -> None:
    content = tmp_path / "content"
    content.mkdir()
    raw_digest = "a" * 64
    basename = "BTCUSDT-1h-2026-07.zip"
    body = f"{raw_digest}  {basename}\n".encode()
    sidecar_digest = hashlib.sha256(body).hexdigest()
    directory = content / sidecar_digest[:2]
    directory.mkdir()
    path = directory / sidecar_digest
    path.write_bytes(body)
    arguments = {
        "zip_basename": basename,
        "content_sha256": raw_digest,
        "completion_sidecar_sha256": sidecar_digest,
        "completion_sidecar_path": path,
        "fact_sidecar_sha256": sidecar_digest,
        "fact_sidecar_path": path,
        "fact_sidecar_bytes": len(body),
        "provider_checksum": raw_digest,
    }
    ps._authenticate_checksum_sidecar(content, **arguments)
    for field, bad in (
        ("completion_sidecar_sha256", "b" * 64),
        ("completion_sidecar_path", tmp_path / "wrong"),
        ("fact_sidecar_sha256", "c" * 64),
        ("fact_sidecar_path", tmp_path / "wrong"),
        ("fact_sidecar_bytes", len(body) + 1),
        ("provider_checksum", "d" * 64),
    ):
        changed = dict(arguments)
        changed[field] = bad
        with pytest.raises(ps.PriceStateNormalizationError):
            ps._authenticate_checksum_sidecar(content, **changed)
    path.unlink()
    with pytest.raises(ps.PriceStateNormalizationError, match="reachable"):
        ps._authenticate_checksum_sidecar(content, **arguments)
    target = tmp_path / "sidecar-target"
    target.write_bytes(body)
    path.symlink_to(target)
    with pytest.raises(ps.PriceStateNormalizationError, match="symlink"):
        ps._authenticate_checksum_sidecar(content, **arguments)
    path.unlink()
    path.write_bytes(body + b"tamper")
    with pytest.raises(ps.PriceStateNormalizationError, match="size|digest"):
        ps._authenticate_checksum_sidecar(content, **arguments)
    for statement, match in (
        (f"{'e' * 64}  {basename}\n".encode(), "checksum"),
        (f"{raw_digest}  ETHUSDT-1h-2026-07.zip\n".encode(), "basename"),
    ):
        statement_digest = hashlib.sha256(statement).hexdigest()
        statement_directory = content / statement_digest[:2]
        statement_directory.mkdir(exist_ok=True)
        statement_path = statement_directory / statement_digest
        statement_path.write_bytes(statement)
        changed = {
            **arguments,
            "completion_sidecar_sha256": statement_digest,
            "completion_sidecar_path": statement_path,
            "fact_sidecar_sha256": statement_digest,
            "fact_sidecar_path": statement_path,
            "fact_sidecar_bytes": len(statement),
        }
        with pytest.raises(ps.PriceStateNormalizationError, match=match):
            ps._authenticate_checksum_sidecar(content, **changed)


def test_minimal_substitute_generation0_database_is_rejected(tmp_path: Path) -> None:
    state = tmp_path / "state.sqlite"
    connection = sqlite3.connect(state)
    connection.execute("CREATE TABLE substitute(value TEXT)")
    connection.commit()
    connection.close()
    content = tmp_path / "content"
    content.mkdir()
    with pytest.raises(RuntimeError):
        ps.load_generation0_sources(state, content)


def test_pinned_authority_and_corrected_retained_inventory() -> None:
    assert ps.ACCEPTED_SOURCE_COUNT == 102_740
    assert ps.ACCEPTED_SOURCE_BYTES == 1_038_628_891
    assert ps.ACCEPTED_CHECKSUM_VERIFIED == 102_711
    assert ps.ACCEPTED_RETAINED == 29
    assert ps.ACCEPTED_FAMILY_RETAINED["monthly/markPriceKlines"] == 9
    assert ps.ACCEPTED_PREMIUM_SOURCES == 32_371
    assert ps.ACCEPTED_UNION_PARTITIONS == 23_268
    assert ps.ACCEPTED_JOINABLE_PARTITIONS == 21_491


def test_pinned_json_digest_tamper_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "authority.json"
    path.write_text("{}\n")
    with pytest.raises(ps.PriceStateNormalizationError, match="digest changed"):
        ps._read_pinned_json(path, "0" * 64, 1024)


def test_sizing_pins_both_schemas_writer_policy_and_ceilings(tmp_path: Path) -> None:
    sources = _triplet(tmp_path)
    cases = [
        ("schema", lambda value: value["projections"]["final_product_schemas"][ps.INDICATIVE_PRODUCT].pop()),
        ("writer", lambda value: value["code_identity"].update(writer_identity="changed")),
        ("policy", lambda value: value["code_identity"].update(policy_identity="changed")),
        ("projected_rows", lambda value: value["projections"]["required_products"][0].update(projected_rows=1)),
        ("report binding", lambda value: value["authority"]["bindings"].update(report_sha256="0" * 64)),
    ]
    for match, mutate in cases:
        candidate = deepcopy(_sizing())
        mutate(candidate)
        output = tmp_path / match.replace(" ", "-")
        output.mkdir()
        with pytest.raises(ps.PriceStateNormalizationError, match=match):
            _normalize(output, sources, sizing=candidate, report=_report())


def test_compact_join_lineage_roundtrips_refs_ordinals_and_runs(tmp_path: Path) -> None:
    moments = [JULY + offset * HOUR for offset in range(3)]
    result = _normalize(
        tmp_path,
        _triplet(
            tmp_path,
            mark_rows=[_line(moment, close="2") for moment in moments],
            index_rows=[_line(moment, close="3") for moment in moments],
            premium_rows=[_premium_line(moment) for moment in moments],
        ),
    )
    lineage = json.loads(result.basis.partitions[0].lineage_path.read_text())
    assert len(lineage["raw_objects"]) == 3
    assert len(lineage["joined_source_runs"]) == 1
    run = lineage["joined_source_runs"][0]
    assert run["row_count"] == 3
    assert run["open_time_start_ms"] == JULY
    assert run["open_time_end_ms"] == JULY + 2 * HOUR
    for kind in ps.KINDS:
        ref = run[f"{kind}_raw_object_ref"]
        assert lineage["raw_objects"][ref]["kind"] == kind
        assert run[f"{kind}_source_row_ordinal_start"] == 0
        assert run[f"{kind}_source_row_ordinal_end"] == 2
    encoded = json.dumps(lineage["joined_source_runs"], separators=(",", ":"))
    assert "data/futures" not in encoded


def test_wholly_unjoinable_month_is_one_maximal_gap_run(tmp_path: Path) -> None:
    august = JULY + 31 * 24 * HOUR
    rows = [_line(august + offset * HOUR, close="3") for offset in range(24)]
    sources = _triplet(tmp_path)
    sources.append(_source(tmp_path, ps.INDEX, "2026-08-01", rows, suffix="-only"))
    result = _normalize(tmp_path, sources)
    gap = next(item for item in result.basis.gap_artifacts if item.utc_month == "2026-08")
    table = pq.read_table(gap.parquet_path)
    assert table.num_rows == 1
    assert table.column("expected_grid_count").to_pylist() == [24]
    lineage = json.loads(gap.lineage_path.read_text())
    assert lineage["unjoinable_source_rows"] == 24
    assert len(lineage["unjoinable_observations"]) == 1
    run = lineage["unjoinable_observations"][0]
    assert run["source_row_count"] == 24
    assert run["source_row_ordinal_start"] == 0
    assert run["source_row_ordinal_end"] == 23
    assert "source_key" not in run


def test_duplicate_reserved_field_conflict_fails_closed(tmp_path: Path) -> None:
    mark_rows = [_line(JULY, close="2", reserved="0"), _line(JULY, close="2", reserved="1")]
    with pytest.raises(ps.PriceStateNormalizationError, match="conflicting duplicate mark"):
        _normalize(tmp_path, _triplet(tmp_path, mark_rows=mark_rows))


def test_completion_reconciles_each_product_and_declares_floor_semantics(tmp_path: Path) -> None:
    result = _normalize(tmp_path, _triplet(tmp_path), report=_report(), sizing=_sizing())
    indicative = _completion(result.indicative)
    basis = _completion(result.basis)
    assert indicative["row_equation"]["physical_source_rows"] == 1
    assert indicative["row_equation"]["product_rows"] == 1
    assert indicative["row_equation"]["source_decimal_rounding_events"] == 0
    assert basis["row_equation"]["physical_source_rows"] == 3
    assert basis["row_equation"]["joined_input_rows"] == 3
    assert basis["row_equation"]["unjoinable_source_rows"] == 0
    assert basis["row_equation"]["relative_basis_floor_applications"] == 1
    assert basis["partition_reconciliation"] == {
        "source_partition_count": 1,
        "successful_partition_count": 1,
        "gap_only_partition_count": 0,
        "partitions_with_gaps": 0,
    }
    assert basis["qualification_report"]["bound"] is True
    assert basis["schema"] == ps._schema_contract(ps.BASIS_SCHEMA)


def test_byte_identical_replay_reuses_all_artifacts(tmp_path: Path) -> None:
    sources = _triplet(tmp_path)
    first = _normalize(tmp_path, sources)
    bytes_by_path = {
        path: path.read_bytes()
        for path in (
            first.indicative.partitions[0].parquet_path,
            first.indicative.partitions[0].lineage_path,
            first.basis.partitions[0].parquet_path,
            first.basis.partitions[0].lineage_path,
            first.indicative.completion_path,
            first.basis.completion_path,
        )
    }
    second = _normalize(tmp_path, sources)
    assert second.indicative.partitions[0].reused is True
    assert second.basis.partitions[0].reused is True
    assert second.indicative.completion_reused is True
    assert second.basis.completion_reused is True
    assert {path: path.read_bytes() for path in bytes_by_path} == bytes_by_path


def test_completion_is_last_and_interruption_leaves_no_completion(tmp_path: Path) -> None:
    seen: list[tuple[str, str]] = []
    sources = _triplet(tmp_path)

    def interrupt(product: str, kind: str, _stage: Path, _destination: Path) -> None:
        seen.append((product, kind))
        if kind == "completion":
            raise RuntimeError("stop-before-completion")

    with pytest.raises(RuntimeError, match="stop-before-completion"):
        _normalize(tmp_path, sources, hooks=ps.PublicationHooks(before_publish=interrupt))
    assert seen[-1][1] == "completion"
    assert not list((tmp_path / ".price-state").rglob(".complete/*.json"))
    resumed = _normalize(tmp_path, sources)
    assert resumed.indicative.partitions[0].reused is True
    assert resumed.indicative.completion_path.is_file()
    assert resumed.basis.completion_path.is_file()


def test_partition_interruption_has_no_visible_product_completion(tmp_path: Path) -> None:
    def interrupt(_product: str, kind: str, _stage: Path, _destination: Path) -> None:
        if kind == "partition":
            raise RuntimeError("partition-stop")

    with pytest.raises(RuntimeError, match="partition-stop"):
        _normalize(tmp_path, _triplet(tmp_path), hooks=ps.PublicationHooks(before_publish=interrupt))
    assert not list((tmp_path / ".price-state").rglob(".complete/*.json"))


def test_existing_content_address_is_never_clobbered(tmp_path: Path) -> None:
    sources = _triplet(tmp_path)
    first = _normalize(tmp_path, sources)
    victim = first.basis.partitions[0].parquet_path
    victim.write_bytes(b"tampered")
    with pytest.raises(ps.PriceStateNormalizationError, match="replay differs|Parquet"):
        _normalize(tmp_path, sources)
    assert victim.read_bytes() == b"tampered"


def test_existing_different_completion_blocks_republication(tmp_path: Path) -> None:
    sources = _triplet(tmp_path)
    first = _normalize(tmp_path, sources)
    extra = first.basis.completion_path.parent / f"{'f' * 64}.json"
    extra.write_text("{}\n")
    with pytest.raises(ps.PriceStateNormalizationError, match="another.*completion"):
        _normalize(tmp_path, sources)
    assert extra.read_text() == "{}\n"


def test_concurrent_root_lock_fails_without_clobber(tmp_path: Path) -> None:
    root = tmp_path / ".price-state"
    first = ps._OutputTree(root)
    try:
        with pytest.raises(ps.PriceStateNormalizationError, match="another normalizer"):
            ps._OutputTree(root)
    finally:
        first.close()


def test_output_root_and_existing_children_reject_symlinks(tmp_path: Path) -> None:
    sources = _triplet(tmp_path)
    with pytest.raises(ps.PriceStateNormalizationError, match="hidden"):
        ps.normalize_price_state_sources(sources, tmp_path / "visible")
    root = tmp_path / ".unsafe"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (root / ps.INDICATIVE_PRODUCT).symlink_to(target, target_is_directory=True)
    with pytest.raises(ps.PriceStateNormalizationError, match="unsafe"):
        ps.normalize_price_state_sources(sources, root)


def test_processing_is_symbol_month_bounded_and_reads_each_premium_zip_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    august = JULY + 31 * 24 * HOUR
    sources = _triplet(tmp_path)
    sources.extend(
        [
            _source(tmp_path, ps.PREMIUM, "2026-08", [_premium_line(august)], suffix="-aug"),
            _source(tmp_path, ps.MARK, "2026-08", [_line(august, close="2")], suffix="-aug"),
            _source(tmp_path, ps.INDEX, "2026-08", [_line(august, close="3")], suffix="-aug"),
        ]
    )

    class TrackedRecord(dict[str, object]):
        __hash__ = object.__hash__

    live: weakref.WeakSet[TrackedRecord] = weakref.WeakSet()
    original_iter = ps._iter_rows

    def tracked_iter(source: ps.RawPriceStateObject):
        for record in original_iter(source):
            tracked = TrackedRecord(record)
            live.add(tracked)
            yield tracked

    observed_live: list[int] = []

    def observe(_product: str, kind: str, _stage: Path, destination: Path) -> None:
        if kind == "partition" and "2026-08" in destination.parts:
            observed_live.append(len(live))

    monkeypatch.setattr(ps, "_iter_rows", tracked_iter)
    result = _normalize(
        tmp_path,
        sources,
        hooks=ps.PublicationHooks(before_publish=observe),
    )
    assert result.premium_zip_reads == 2
    assert [(part.native_symbol, part.utc_month) for part in result.indicative.partitions] == [
        ("BTCUSDT", "2026-07"),
        ("BTCUSDT", "2026-08"),
    ]
    assert len(result.basis.partitions) == 2
    assert observed_live and max(observed_live) <= 3
