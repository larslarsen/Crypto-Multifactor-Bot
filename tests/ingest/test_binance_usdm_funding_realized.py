"""Focused production-contract tests for USD-M realized funding events."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
import zipfile
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, localcontext
from io import BytesIO
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from cryptofactors.ingest import binance_usdm_funding_realized as funding


HEADER = ",".join(funding.FUNDING_FIELDS)
JULY = 1_782_864_000_000


def _line(calc_time: int, interval: str = "8", rate: str = "0.000100000000000000") -> str:
    return f"{calc_time},{interval},{rate}"


def _key(symbol: str, period: str) -> str:
    return f"data/futures/um/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{period}.zip"


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
    headed: bool = True,
    payload: bytes | None = None,
    state: str = funding.OUTCOME_CHECKSUM_VERIFIED,
) -> funding.RawFundingObject:
    key = _key(symbol, period)
    body = payload if payload is not None else _zip_bytes(key, rows, headed=headed)
    path = tmp_path / f"{symbol}-{period}.zip"
    path.write_bytes(body)
    return funding.RawFundingObject(
        source_key=key,
        family=funding.FAMILY,
        native_symbol=symbol,
        economic_period=period,
        path=path,
        source_sha256=hashlib.sha256(body).hexdigest(),
        byte_size=len(body),
        validation_state=state,
        retrieval_time="2026-09-02T00:00:00Z",
    )


def _report(gaps: list[dict[str, object]] | None = None, kinds: list[str] | None = None, typed: list[str] | None = None) -> dict[str, object]:
    gap_rows = gaps if gaps is not None else []
    return {
        "product_matrix": [
            {
                "product": funding.PRODUCT,
                "universe_coverage_gaps": gap_rows,
                "typed_gap_symbols": typed if typed is not None else [],
                "coverage_gap_kinds": kinds if kinds is not None else [],
                "accepted_universe_object_count": 1,
                "accepted_universe_listed_bytes": 1,
            }
        ],
        "storage": {"universe_coverage_gaps": {funding.PRODUCT: gap_rows}},
    }


def _sizing() -> dict[str, object]:
    return {
        "authority": {"bindings": {"report_sha256": funding.REPORT_SHA256}},
        "code_identity": {
            "policy_identity": funding.SIZING_POLICY_IDENTITY,
            "writer_identity": funding.writer_identity(),
        },
        "projections": {
            "final_product_schemas": {funding.PRODUCT: funding._schema_contract()},
            "required_products": [
                {
                    "required_product": funding.PRODUCT,
                    "projected_rows": funding.ACCEPTED_PROJECTED_ROWS,
                    "projected_bytes": funding.ACCEPTED_PROJECTED_BYTES,
                    "partition_count": funding.ACCEPTED_SOURCE_COUNT,
                    "largest_partition_bytes": funding.ACCEPTED_LARGEST_PARTITION_BYTES,
                    "input_objects": funding.ACCEPTED_SOURCE_COUNT,
                    "input_compressed_bytes": funding.ACCEPTED_SOURCE_BYTES,
                }
            ],
        },
    }


def _normalize(
    tmp_path: Path,
    sources: list[funding.RawFundingObject],
    *,
    report: dict[str, object] | None = None,
    sizing: dict[str, object] | None = None,
    hooks: funding.PublicationHooks = funding.PublicationHooks(),
) -> funding.FundingNormalizationResult:
    return funding.normalize_funding_sources(
        sources,
        tmp_path / ".funding",
        report=report,
        sizing=sizing,
        hooks=hooks,
    )


def _table(result: funding.FundingNormalizationResult):
    assert len(result.partitions) == 1
    return pq.read_table(result.partitions[0].parquet_path)


def _completion(result: funding.FundingNormalizationResult) -> dict[str, object]:
    return json.loads(result.completion_path.read_text())


def test_exact_14_column_schema_and_native_only_identity(tmp_path: Path) -> None:
    result = _normalize(tmp_path, [_source(tmp_path, "2026-07", [_line(JULY)])])
    assert len(funding.SCHEMA) == 14
    assert funding.SCHEMA.names == [
        "raw_object_ref",
        "source_row_ordinal",
        "venue_symbol",
        "calc_time",
        "funding_interval_hours",
        "last_funding_rate",
        "venue",
        "native_symbol",
        "canonical_instrument_id",
        "canonical_instrument_version_id",
        "reference_identity_state",
        "long_cashflow_rate",
        "short_cashflow_rate",
        "cashflow_sign_convention",
    ]
    table = _table(result)
    assert table.schema == funding.SCHEMA
    assert table.column("venue").to_pylist() == ["BINANCE_USDM"]
    assert table.column("native_symbol").to_pylist() == ["BTCUSDT"]
    assert table.column("venue_symbol").to_pylist() == ["BTCUSDT"]
    assert table.column("canonical_instrument_id").to_pylist() == [None]
    assert table.column("canonical_instrument_version_id").to_pylist() == [None]
    assert table.column("reference_identity_state").to_pylist() == ["reference_identity_not_yet_created"]


@pytest.mark.parametrize("headed", [True, False])
def test_headed_and_headerless_rows_publish_exact_schema(tmp_path: Path, headed: bool) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY)], headed=headed)
    table = _table(_normalize(tmp_path, [source]))
    assert table.schema == funding.SCHEMA
    assert table.column("calc_time").to_pylist() == [JULY]
    assert table.column("funding_interval_hours").to_pylist() == [8]


def test_positive_negative_and_zero_cashflow_are_exact_and_conserved(tmp_path: Path) -> None:
    rows = [
        _line(JULY, "8", "0.000100000000000001"),
        _line(JULY + 8 * 3_600_000, "8", "-0.000200000000000002"),
        _line(JULY + 16 * 3_600_000, "8", "0"),
    ]
    table = _table(_normalize(tmp_path, [_source(tmp_path, "2026-07", rows)]))
    long_rates = table.column("long_cashflow_rate").to_pylist()
    short_rates = table.column("short_cashflow_rate").to_pylist()
    last_rates = table.column("last_funding_rate").to_pylist()
    assert last_rates == [
        Decimal("0.000100000000000001"),
        Decimal("-0.000200000000000002"),
        Decimal("0E-18"),
    ]
    assert long_rates == [
        Decimal("-0.000100000000000001"),
        Decimal("0.000200000000000002"),
        Decimal("0E-18"),
    ]
    assert short_rates == last_rates
    for long_rate, short_rate in zip(long_rates, short_rates, strict=True):
        assert long_rate + short_rate == Decimal("0")
    assert table.column("cashflow_sign_convention").to_pylist() == [funding.CASHFLOW_SIGN_CONVENTION] * 3


def test_interval_transition_does_not_invent_rows_or_rescale_rates(tmp_path: Path) -> None:
    rows = [
        _line(JULY, "8", "0.000100000000000000"),
        _line(JULY + 8 * 3_600_000, "4", "0.000100000000000000"),
        _line(JULY + 12 * 3_600_000, "1", "0.000100000000000000"),
        _line(JULY + 13 * 3_600_000, "8", "0.000100000000000000"),
    ]
    result = _normalize(tmp_path, [_source(tmp_path, "2026-07", rows)])
    table = _table(result)
    assert table.num_rows == 4
    assert table.column("funding_interval_hours").to_pylist() == [8, 4, 1, 8]
    assert table.column("last_funding_rate").to_pylist() == [Decimal("0.000100000000000000")] * 4
    complete = _completion(result)
    assert complete["row_equation"] == {
        "physical_source_rows": 4,
        "collapsed_identical_rows": 0,
        "excluded_source_rows": 0,
        "inferred_events": 0,
        "rounded_events": 0,
        "conflicting_events": 0,
        "product_rows": 4,
    }
    assert complete["observed_ranges"]["interval_histogram"] == [
        {"event_count": 1, "funding_interval_hours": 1},
        {"event_count": 1, "funding_interval_hours": 4},
        {"event_count": 2, "funding_interval_hours": 8},
    ]


def test_identical_collapse_retains_every_contributing_ordinal(tmp_path: Path) -> None:
    row = _line(JULY)
    result = _normalize(tmp_path, [_source(tmp_path, "2026-07", [row, row])])
    table = _table(result)
    lineage = json.loads(result.partitions[0].lineage_path.read_text())
    complete = _completion(result)
    assert table.num_rows == 1
    assert table.column("source_row_ordinal").to_pylist() == [0]
    assert lineage["collapsed_identical_row_count"] == 1
    assert lineage["collapsed_identical_source_rows"] == [
        {
            "calc_time": JULY,
            "collapsed_raw_object_ref": 0,
            "collapsed_source_row_ordinal": 1,
            "funding_interval_hours": 8,
            "kept_raw_object_ref": 0,
            "kept_source_key": result.partitions[0].lineage_path and lineage["raw_objects"][0]["source_key"],
            "kept_source_row_ordinal": 0,
            "kept_source_sha256": lineage["raw_objects"][0]["source_sha256"],
            "last_funding_rate": "0.000100000000000000",
            "reason": funding.IDENTICAL_OBSERVED_SETTLEMENT,
            "source_key": lineage["raw_objects"][0]["source_key"],
            "source_sha256": lineage["raw_objects"][0]["source_sha256"],
        }
    ]
    assert complete["row_equation"]["physical_source_rows"] == 2
    assert complete["row_equation"]["collapsed_identical_rows"] == 1
    assert complete["row_equation"]["product_rows"] == 1


def test_repeated_timestamp_with_conflicting_rate_or_interval_fails(tmp_path: Path) -> None:
    with pytest.raises(funding.FundingNormalizationError, match="conflicting"):
        _normalize(tmp_path, [_source(tmp_path, "2026-07", [_line(JULY, "8", "0.1"), _line(JULY, "8", "0.2")])])
    with pytest.raises(funding.FundingNormalizationError, match="conflicting"):
        _normalize(tmp_path, [_source(tmp_path, "2026-07", [_line(JULY, "8"), _line(JULY, "4")])])


def test_complete_lineage_maps_each_raw_object_exactly_once(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY), _line(JULY + 8 * 3_600_000)])
    result = _normalize(tmp_path, [source])
    lineage = json.loads(result.partitions[0].lineage_path.read_text())
    table = _table(result)
    assert lineage["raw_objects"] == [
        {
            "byte_size": source.byte_size,
            "checksum_authority": funding.CHECKSUM_AUTHORITY,
            "economic_period": "2026-07",
            "family": funding.FAMILY,
            "listed_bytes": source.byte_size,
            "native_symbol": "BTCUSDT",
            "raw_object_ref": 0,
            "retrieval_time": "2026-09-02T00:00:00Z",
            "sidecar_key": f"{source.source_key}.CHECKSUM",
            "source_availability_state": funding.UNKNOWN_AVAILABILITY,
            "source_available_at": None,
            "source_key": source.source_key,
            "source_sha256": source.source_sha256,
            "validation_state": funding.OUTCOME_CHECKSUM_VERIFIED,
        }
    ]
    assert table.column("raw_object_ref").to_pylist() == [0, 0]
    assert table.column("source_row_ordinal").to_pylist() == [0, 1]
    complete = _completion(result)
    assert complete["authority_sha256"]["report"] == funding.REPORT_SHA256
    assert complete["authority_sha256"]["sizing"] == funding.SIZING_SHA256
    assert complete["authority_sha256"]["schema"] == funding.SCHEMA_SHA256
    assert complete["partitions"][0]["lineage_sha256"] == result.partitions[0].lineage_sha256


def test_rows_are_ordered_by_symbol_time_source_and_ordinal(tmp_path: Path) -> None:
    eth = _source(tmp_path, "2026-07", [_line(JULY + 8 * 3_600_000), _line(JULY)], symbol="ETHUSDT")
    btc = _source(tmp_path, "2026-07", [_line(JULY + 8 * 3_600_000), _line(JULY)], symbol="BTCUSDT")
    result = _normalize(tmp_path, [eth, btc])
    assert [item.native_symbol for item in result.partitions] == ["BTCUSDT", "ETHUSDT"]
    first = pq.read_table(result.partitions[0].parquet_path)
    assert first.column("calc_time").to_pylist() == [JULY, JULY + 8 * 3_600_000]
    assert first.column("source_row_ordinal").to_pylist() == [1, 0]


def test_unknown_publication_time_is_not_copied_from_calc_time(tmp_path: Path) -> None:
    result = _normalize(tmp_path, [_source(tmp_path, "2026-07", [_line(JULY)])])
    lineage = json.loads(result.partitions[0].lineage_path.read_text())
    assert lineage["raw_objects"][0]["source_available_at"] is None
    assert lineage["raw_objects"][0]["source_availability_state"] == funding.UNKNOWN_AVAILABILITY


@pytest.mark.parametrize(
    "row,match",
    [
        (_line(JULY, "0"), "positive"),
        (_line(JULY, "-1"), "positive"),
        (_line(JULY, "8.0"), "exact integer"),
        (_line(JULY, "8", "0.1.2"), "exact decimal"),
        (_line(JULY, "8", "nan"), "exact decimal"),
        ("not-an-int,8,0.1", "exact integer"),
        (f"{JULY},8", "width"),
        (f"{JULY},8,0.1,extra", "width"),
        (str(JULY + 32 * 86_400_000) + ",8,0.1", "source month"),
    ],
)
def test_strict_integers_decimals_and_month_identity_fail_closed(
    tmp_path: Path,
    row: str,
    match: str,
) -> None:
    with pytest.raises(funding.FundingNormalizationError, match=match):
        _normalize(tmp_path, [_source(tmp_path, "2026-07", [row])])
    assert not list((tmp_path / ".funding" / ".complete").glob("*.json"))


def test_arbitrary_first_row_is_not_treated_as_a_header(tmp_path: Path) -> None:
    with pytest.raises(funding.FundingNormalizationError, match="exact integer"):
        _normalize(tmp_path, [_source(tmp_path, "2026-07", ["x,y,z"], headed=False)])


def test_cashflow_negation_is_independent_of_ambient_decimal_context(tmp_path: Path) -> None:
    with localcontext() as context:
        context.prec = 4
        table = _table(_normalize(tmp_path, [_source(tmp_path, "2026-07", [_line(JULY, "8", "0.000123456789012345")])]))
    assert table.column("last_funding_rate").to_pylist() == [Decimal("0.000123456789012345")]
    assert table.column("long_cashflow_rate").to_pylist() == [Decimal("-0.000123456789012345")]


def test_non_whitelisted_positive_interval_is_preserved(tmp_path: Path) -> None:
    table = _table(_normalize(tmp_path, [_source(tmp_path, "2026-07", [_line(JULY, "12")])]))
    assert table.column("funding_interval_hours").to_pylist() == [12]


@pytest.mark.parametrize("member", ["../escape.csv", "/absolute.csv", "nested/file.csv", "wrong.csv"])
def test_unsafe_zip_member_paths_are_rejected(tmp_path: Path, member: str) -> None:
    key = _key("BTCUSDT", "2026-07")
    payload = _zip_bytes(key, [_line(JULY)], member=member)
    with pytest.raises(funding.FundingNormalizationError):
        _normalize(tmp_path, [_source(tmp_path, "2026-07", [], payload=payload)])


def test_symlink_encrypted_and_multi_member_zips_are_rejected(tmp_path: Path) -> None:
    target = BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        info = zipfile.ZipInfo("BTCUSDT-fundingRate-2026-07.csv")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, b"target")
    with pytest.raises(funding.FundingNormalizationError, match="regular"):
        _normalize(tmp_path, [_source(tmp_path, "2026-07", [], payload=target.getvalue())])

    target = BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("BTCUSDT-fundingRate-2026-07.csv", _line(JULY))
        archive.filelist[0].flag_bits |= 0x1
    with pytest.raises(funding.FundingNormalizationError, match="encrypted"):
        _normalize(tmp_path, [_source(tmp_path, "2026-07", [], payload=target.getvalue())])

    target = BytesIO()
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("BTCUSDT-fundingRate-2026-07.csv", _line(JULY))
        archive.writestr("extra.csv", "x")
    with pytest.raises(funding.FundingNormalizationError, match="exactly one"):
        _normalize(tmp_path, [_source(tmp_path, "2026-07", [], payload=target.getvalue())])


def test_crc_invalid_zip_is_rejected(tmp_path: Path) -> None:
    marker = b"1782864000000"
    target = BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("BTCUSDT-fundingRate-2026-07.csv", marker + b",8,0.0001\n")
    corrupted = bytearray(target.getvalue())
    position = corrupted.index(marker)
    corrupted[position] ^= 1
    with pytest.raises(funding.FundingNormalizationError):
        _normalize(tmp_path, [_source(tmp_path, "2026-07", [], payload=bytes(corrupted))])


def test_8193rd_row_exceeds_finite_parser_bound(tmp_path: Path) -> None:
    row = _line(JULY)
    with pytest.raises(funding.FundingNormalizationError, match="row parser bound"):
        _normalize(tmp_path, [_source(tmp_path, "2026-07", [row] * (funding.MAX_ROWS_PER_OBJECT + 1))])


def test_key_member_symbol_and_month_must_agree(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY)])
    with pytest.raises(funding.FundingNormalizationError, match="conflicts"):
        _normalize(tmp_path, [replace(source, source_key=_key("ETHUSDT", "2026-07"))])
    with pytest.raises(funding.FundingNormalizationError, match="conflicts"):
        _normalize(tmp_path, [replace(source, native_symbol="ETHUSDT")])
    with pytest.raises(funding.FundingNormalizationError, match="source month"):
        _normalize(tmp_path, [_source(tmp_path, "2026-06", [_line(JULY)])])


def test_duplicate_partition_authority_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY)])
    with pytest.raises(funding.FundingNormalizationError, match="repeats|partition"):
        _normalize(tmp_path, [source, source])


def test_completion_reconciles_physical_collapsed_and_product_rows(tmp_path: Path) -> None:
    rows = [_line(JULY), _line(JULY), _line(JULY + 8 * 3_600_000)]
    result = _normalize(tmp_path, [_source(tmp_path, "2026-07", rows)], report=_report(), sizing=_sizing())
    complete = _completion(result)
    assert complete["row_equation"]["physical_source_rows"] - complete["row_equation"]["collapsed_identical_rows"] == complete["row_equation"]["product_rows"]
    assert complete["row_equation"]["excluded_source_rows"] == 0
    assert complete["row_equation"]["inferred_events"] == 0
    assert complete["row_equation"]["rounded_events"] == 0
    assert complete["row_equation"]["conflicting_events"] == 0
    assert complete["source_gap_authority"]["bound"] is True
    assert complete["sizing_ceiling"]["projected_rows"] == funding.ACCEPTED_PROJECTED_ROWS
    assert result.physical_source_rows == 3
    assert result.collapsed_identical_rows == 1
    assert result.product_rows == 2


def test_byte_identical_replay_reuses_every_artifact(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY)])
    first = _normalize(tmp_path, [source])
    first_bytes = first.completion_path.read_bytes()
    second = _normalize(tmp_path, [source])
    assert second.partitions[0].reused is True
    assert second.completion_reused is True
    assert second.completion_path.read_bytes() == first_bytes
    assert second.completion_sha256 == first.completion_sha256


def test_interruption_leaves_no_product_completion(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY)])
    observed: list[str] = []

    def interrupt(kind: str, _stage: Path, _destination: Path) -> None:
        observed.append(kind)
        if kind == "completion":
            raise RuntimeError("stop-before-completion")

    with pytest.raises(RuntimeError, match="stop-before-completion"):
        _normalize(tmp_path, [source], hooks=funding.PublicationHooks(before_publish=interrupt))
    assert observed[-1] == "completion"
    completed = tmp_path / ".funding" / ".complete"
    assert not completed.exists() or not list(completed.iterdir())
    resumed = _normalize(tmp_path, [source])
    assert resumed.partitions[0].reused is True
    assert resumed.completion_path.is_file()


def test_existing_content_address_is_never_clobbered(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY)])
    first = _normalize(tmp_path, [source])
    victim = first.partitions[0].parquet_path
    victim.write_bytes(b"tampered")
    with pytest.raises(funding.FundingNormalizationError, match="replay differs|published Parquet"):
        _normalize(tmp_path, [source])
    assert victim.read_bytes() == b"tampered"


def test_partition_publish_interrupt_leaves_no_visible_complete_product(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY)])

    def interrupt(kind: str, _stage: Path, _destination: Path) -> None:
        if kind == "partition":
            raise RuntimeError("injected partition interruption")

    output = tmp_path / ".funding"
    with pytest.raises(RuntimeError, match="injected"):
        _normalize(tmp_path, [source], hooks=funding.PublicationHooks(before_publish=interrupt))
    assert not (output / ".complete").exists() or not list((output / ".complete").glob("*.json"))
    assert not list(output.rglob("*.parquet"))


def test_pinned_authority_constants_and_digest_tamper_are_rejected(tmp_path: Path) -> None:
    assert funding.REPORT_SHA256 == "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
    assert funding.SIZING_SHA256 == "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589"
    assert funding.ACCEPTED_SOURCE_COUNT == 21_035
    assert funding.ACCEPTED_SOURCE_BYTES == 21_351_804
    assert funding.ACCEPTED_CHECKSUM_VERIFIED_SOURCES == 21_020
    assert funding.ACCEPTED_RETAINED_CREDIT_SOURCES == 15
    assert funding.ACCEPTED_COVERAGE_GAP_ROWS == 959
    assert funding.ACCEPTED_TYPED_GAP_SYMBOLS == 675
    assert funding.ACCEPTED_COVERAGE_GAP_KINDS == (
        "current_unarchived",
        "head_gap_family_launch",
        "head_gap_pre_listing",
        "head_gap_unexplained",
        "head_gap_unknown_onboard",
        "interior_month_gap",
        "tail_gap_missing_recent",
        "tail_gap_post_close",
        "tail_gap_unknown_close",
    )
    authority = tmp_path / "authority.json"
    authority.write_text("{}\n")
    with pytest.raises(funding.FundingNormalizationError, match="digest changed"):
        funding._read_pinned_json(authority, "0" * 64, 1024)


def test_sizing_schema_writer_policy_and_ceilings_are_pinned(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY)])
    cases = [
        ("schema", lambda value: value["projections"]["final_product_schemas"][funding.PRODUCT].pop()),
        ("writer", lambda value: value["code_identity"].update(writer_identity="changed")),
        ("policy", lambda value: value["code_identity"].update(policy_identity="changed")),
        ("projected rows", lambda value: value["projections"]["required_products"][0].update(projected_rows=1)),
        ("report binding", lambda value: value["authority"]["bindings"].update(report_sha256="b" * 64)),
    ]
    for message, mutate in cases:
        candidate = deepcopy(_sizing())
        mutate(candidate)
        with pytest.raises(funding.FundingNormalizationError, match=message):
            _normalize(tmp_path, [source], report=_report(), sizing=candidate)


def test_report_coverage_authority_is_bound_and_not_expanded(tmp_path: Path) -> None:
    gaps = [
        {
            "symbol": "BTCUSDT",
            "kind": "head_gap_pre_listing",
            "blocking": False,
        }
    ]
    kinds = ["head_gap_pre_listing"]
    result = _normalize(
        tmp_path,
        [_source(tmp_path, "2026-07", [_line(JULY)])],
        report=_report(gaps=gaps, kinds=kinds, typed=["BTCUSDT"]),
        sizing=_sizing(),
    )
    complete = _completion(result)
    assert complete["source_gap_authority"] == {
        "bound": True,
        "coverage_gap_kinds": ["head_gap_pre_listing"],
        "coverage_gap_rows": 1,
        "report_sha256": funding.REPORT_SHA256,
        "typed_gap_symbol_count": 1,
    }
    assert result.product_rows == 1


def test_full_corpus_report_counts_are_enforced() -> None:
    report = _report()
    with pytest.raises(funding.FundingNormalizationError, match="coverage-gap count"):
        funding._validate_report(report, enforce_full_corpus=True)


@pytest.mark.parametrize("state", [funding.OUTCOME_CHECKSUM_VERIFIED, funding.OUTCOME_RETAINED])
def test_only_accepted_generation0_validation_states_pass(state: str) -> None:
    funding._require_accepted_validation_state(state)


def test_unknown_generation0_validation_state_is_rejected() -> None:
    with pytest.raises(funding.FundingNormalizationError, match="not accepted"):
        funding._require_accepted_validation_state("unknown")


def test_plan_payload_must_bind_identity_family_symbol_period_bytes_and_sidecar() -> None:
    identity = _key("BTCUSDT", "2026-07")
    payload = {
        "key": identity,
        "family": funding.FAMILY,
        "symbol": "BTCUSDT",
        "economic_interval": "2026-07",
        "listed_bytes": 123,
        "sidecar_key": f"{identity}.CHECKSUM",
    }
    assert funding._validate_plan_payload(identity, payload, 123) == ("BTCUSDT", "2026-07")
    for field in ("key", "family", "symbol", "economic_interval", "listed_bytes", "sidecar_key"):
        changed = dict(payload)
        changed[field] = "wrong"
        with pytest.raises(funding.FundingNormalizationError):
            funding._validate_plan_payload(identity, changed, 123)


def test_minimal_substitute_generation0_database_is_rejected(tmp_path: Path) -> None:
    state = tmp_path / "state.sqlite"
    connection = sqlite3.connect(state)
    connection.execute("CREATE TABLE substitute(value TEXT)")
    connection.commit()
    connection.close()
    content = tmp_path / "content"
    content.mkdir()
    with pytest.raises(RuntimeError):
        funding.load_generation0_sources(state, content)


def test_source_checksum_and_symlink_substitution_fail(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY)])
    with pytest.raises(funding.FundingNormalizationError, match="bytes"):
        _normalize(tmp_path, [replace(source, source_sha256="0" * 64)])
    link = tmp_path / "source-link.zip"
    link.symlink_to(source.path)
    with pytest.raises(funding.FundingNormalizationError, match="symlink"):
        _normalize(tmp_path, [replace(source, path=link)])


def test_output_root_must_be_hidden(tmp_path: Path) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY)])
    with pytest.raises(funding.FundingNormalizationError, match="hidden"):
        funding.normalize_funding_sources([source], tmp_path / "funding")


def test_authority_and_output_symlinks_are_rejected(tmp_path: Path) -> None:
    authority = tmp_path / "authority.json"
    authority.write_text("{}\n")
    link = tmp_path / "authority-link.json"
    link.symlink_to(authority)
    with pytest.raises(funding.FundingNormalizationError, match="symlink"):
        funding._read_pinned_json(link, hashlib.sha256(b"{}\n").hexdigest(), 1024)
    source = _source(tmp_path, "2026-07", [_line(JULY)])
    output_target = tmp_path / ".target"
    output_target.mkdir()
    output_link = tmp_path / ".funding"
    output_link.symlink_to(output_target, target_is_directory=True)
    with pytest.raises(funding.FundingNormalizationError, match="symlink"):
        funding.normalize_funding_sources([source], output_link)


@pytest.mark.parametrize("symbol", ["../escape", "bad/name", "bad\\name", "", "."])
def test_unsafe_native_symbol_paths_are_rejected(tmp_path: Path, symbol: str) -> None:
    source = _source(tmp_path, "2026-07", [_line(JULY)])
    with pytest.raises(funding.FundingNormalizationError):
        _normalize(tmp_path, [replace(source, native_symbol=symbol, source_key=_key("BTCUSDT", "2026-07"))])


JUNE = JULY - 30 * 86_400_000
CONTENT_SHA = "a" * 64
ZIP_BASENAME = "BTCUSDT-fundingRate-2026-07.zip"


def _plan_payload(identity: str, listed_bytes: int = 123) -> dict[str, object]:
    return {
        "key": identity,
        "family": funding.FAMILY,
        "symbol": "BTCUSDT",
        "economic_interval": "2026-07",
        "listed_bytes": listed_bytes,
        "sidecar_key": f"{identity}.CHECKSUM",
    }


def _plan_envelope(identity: str, listed_bytes: int = 123) -> dict[str, object]:
    return {
        "provider": funding.PROVIDER_BINANCE,
        "identity": identity,
        "kind": funding.KIND_BINANCE,
        "payload": _plan_payload(identity, listed_bytes),
    }


def _sidecar_statement(digest: str, basename: str, *, extra: str = "") -> bytes:
    return f"{digest}  {basename}{extra}\n".encode()


def _write_addressed(root: Path, body: bytes) -> tuple[str, Path]:
    digest = hashlib.sha256(body).hexdigest()
    path = root / digest[:2] / digest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return digest, path


def _authenticate(
    tmp_path: Path,
    body: bytes,
    *,
    content_sha256: str = CONTENT_SHA,
    zip_basename: str = ZIP_BASENAME,
    completion_sha: str | None = None,
    completion_path: Path | None = None,
    fact_sha: str | None = None,
    fact_path: Path | None = None,
    fact_bytes: int | None = None,
    provider_checksum: str | None = None,
    write: bool = True,
) -> None:
    content = tmp_path / "content"
    content.mkdir(exist_ok=True)
    if write:
        digest, path = _write_addressed(content, body)
    else:
        digest = hashlib.sha256(body).hexdigest()
        path = content / digest[:2] / digest
    funding._authenticate_checksum_sidecar(
        content,
        zip_basename=zip_basename,
        content_sha256=content_sha256,
        completion_sidecar_sha256=completion_sha if completion_sha is not None else digest,
        completion_sidecar_path=completion_path if completion_path is not None else path,
        fact_sidecar_sha256=fact_sha if fact_sha is not None else digest,
        fact_sidecar_path=fact_path if fact_path is not None else path,
        fact_sidecar_bytes=len(body) if fact_bytes is None else fact_bytes,
        provider_checksum=content_sha256 if provider_checksum is None else provider_checksum,
    )


def test_incremental_observed_ranges_span_partitions_without_row_retention(
    tmp_path: Path,
) -> None:
    btc_june = _source(tmp_path, "2026-06", [_line(JUNE, "8")], symbol="BTCUSDT")
    btc_july = _source(
        tmp_path,
        "2026-07",
        [_line(JULY, "4"), _line(JULY + 3_600_000, "1")],
        symbol="BTCUSDT",
    )
    eth_july = _source(tmp_path, "2026-07", [_line(JULY, "12")], symbol="ETHUSDT")
    result = _normalize(tmp_path, [eth_july, btc_july, btc_june])
    complete = _completion(result)
    assert [item.native_symbol for item in result.partitions] == [
        "BTCUSDT",
        "BTCUSDT",
        "ETHUSDT",
    ]
    assert [item.utc_month for item in result.partitions] == ["2026-06", "2026-07", "2026-07"]
    assert complete["observed_ranges"] == {
        "calc_time_max": JULY + 3_600_000,
        "calc_time_min": JUNE,
        "funding_interval_hours_max": 12,
        "funding_interval_hours_min": 1,
        "interval_histogram": [
            {"event_count": 1, "funding_interval_hours": 1},
            {"event_count": 1, "funding_interval_hours": 4},
            {"event_count": 1, "funding_interval_hours": 8},
            {"event_count": 1, "funding_interval_hours": 12},
        ],
        "native_symbol_max": "ETHUSDT",
        "native_symbol_min": "BTCUSDT",
    }
    assert result.product_rows == 4


def test_plan_envelope_requires_binance_object_provider_and_identity() -> None:
    identity = _key("BTCUSDT", "2026-07")
    envelope = _plan_envelope(identity)
    assert funding._validate_plan_envelope(identity, envelope, funding.KIND_BINANCE) == envelope["payload"]
    with pytest.raises(funding.FundingNormalizationError, match="plan kind"):
        funding._validate_plan_envelope(identity, envelope, "coinalyze_liquidation")
    for field, value, match in (
        ("provider", "other", "provider"),
        ("identity", "wrong", "identity"),
        ("kind", "other", "kind"),
    ):
        changed = dict(envelope)
        changed[field] = value
        with pytest.raises(funding.FundingNormalizationError, match=match):
            funding._validate_plan_envelope(identity, changed, funding.KIND_BINANCE)


def test_checksum_sidecar_accepts_content_addressed_no_follow_bytes(tmp_path: Path) -> None:
    _authenticate(tmp_path, _sidecar_statement(CONTENT_SHA, ZIP_BASENAME))


def test_completion_and_sidecar_fact_must_agree(tmp_path: Path) -> None:
    body = _sidecar_statement(CONTENT_SHA, ZIP_BASENAME)
    with pytest.raises(funding.FundingNormalizationError, match="digest disagreement"):
        _authenticate(tmp_path, body, completion_sha="b" * 64)
    content = tmp_path / "content"
    digest, path = _write_addressed(content, body)
    other = content / "other"
    other.mkdir()
    relocated = other / digest
    relocated.write_bytes(body)
    with pytest.raises(funding.FundingNormalizationError, match="path disagreement|content address"):
        _authenticate(
            tmp_path,
            body,
            completion_sha=digest,
            completion_path=path,
            fact_sha=digest,
            fact_path=relocated,
            write=False,
        )


def test_sidecar_path_must_be_content_addressed(tmp_path: Path) -> None:
    body = _sidecar_statement(CONTENT_SHA, ZIP_BASENAME)
    content = tmp_path / "content"
    digest, _path = _write_addressed(content, body)
    escaped = tmp_path / "escaped" / digest
    escaped.parent.mkdir()
    escaped.write_bytes(body)
    with pytest.raises(funding.FundingNormalizationError, match="content address"):
        _authenticate(
            tmp_path,
            body,
            completion_sha=digest,
            completion_path=escaped,
            fact_sha=digest,
            fact_path=escaped,
            write=False,
        )


def test_sidecar_symlink_is_not_followed(tmp_path: Path) -> None:
    body = _sidecar_statement(CONTENT_SHA, ZIP_BASENAME)
    digest = hashlib.sha256(body).hexdigest()
    real = tmp_path / "real.checksum"
    real.write_bytes(body)
    content = tmp_path / "content"
    link = content / digest[:2] / digest
    link.parent.mkdir(parents=True)
    link.symlink_to(real)
    with pytest.raises(funding.FundingNormalizationError, match="symlink"):
        _authenticate(
            tmp_path,
            body,
            completion_sha=digest,
            completion_path=link,
            fact_sha=digest,
            fact_path=link,
            write=False,
        )


def test_sidecar_size_and_digest_must_match_recorded_bytes(tmp_path: Path) -> None:
    body = _sidecar_statement(CONTENT_SHA, ZIP_BASENAME)
    with pytest.raises(funding.FundingNormalizationError, match="size changed"):
        _authenticate(tmp_path, body, fact_bytes=len(body) + 1)
    content = tmp_path / "content"
    claimed = "ab" + "c" * 62
    path = content / claimed[:2] / claimed
    path.parent.mkdir(parents=True)
    path.write_bytes(body)
    with pytest.raises(funding.FundingNormalizationError, match="digest changed"):
        _authenticate(
            tmp_path,
            body,
            completion_sha=claimed,
            completion_path=path,
            fact_sha=claimed,
            fact_path=path,
            fact_bytes=len(body),
            write=False,
        )


@pytest.mark.parametrize(
    "body,match",
    [
        (_sidecar_statement(CONTENT_SHA, ZIP_BASENAME, extra=" extra"), "malformed"),
        (_sidecar_statement(CONTENT_SHA, ZIP_BASENAME) + _sidecar_statement(CONTENT_SHA, ZIP_BASENAME), "malformed"),
        (_sidecar_statement(CONTENT_SHA, "other.zip"), "basename"),
        (_sidecar_statement("b" * 64, ZIP_BASENAME), "raw digest"),
    ],
)
def test_sidecar_statement_must_be_exactly_checksum_and_zip_basename(
    tmp_path: Path,
    body: bytes,
    match: str,
) -> None:
    with pytest.raises(funding.FundingNormalizationError, match=match):
        _authenticate(tmp_path, body)


def test_missing_or_nonpositive_sidecar_bytes_fail(tmp_path: Path) -> None:
    body = _sidecar_statement(CONTENT_SHA, ZIP_BASENAME)
    with pytest.raises(funding.FundingNormalizationError, match="positive exact bound"):
        _authenticate(tmp_path, body, fact_bytes=0)
    with pytest.raises(funding.FundingNormalizationError, match="positive exact bound"):
        _authenticate(tmp_path, body, fact_bytes=-1)
    digest = hashlib.sha256(body).hexdigest()
    content = tmp_path / "content"
    path = content / digest[:2] / digest
    path.unlink()
    assert not path.exists()
    with pytest.raises(funding.FundingNormalizationError, match="reachable|missing"):
        _authenticate(
            tmp_path,
            body,
            completion_sha=digest,
            completion_path=path,
            fact_sha=digest,
            fact_path=path,
            write=False,
        )


def test_provider_checksum_must_equal_selected_raw_digest(tmp_path: Path) -> None:
    with pytest.raises(funding.FundingNormalizationError, match="provider/content"):
        _authenticate(
            tmp_path,
            _sidecar_statement(CONTENT_SHA, ZIP_BASENAME),
            provider_checksum="b" * 64,
        )
