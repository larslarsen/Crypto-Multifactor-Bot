"""Focused production-contract tests for USD-M perpetual membership."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from cryptofactors.ingest import binance_usdm_membership as membership


DIGEST = "a" * 64
ENDPOINT = "https://fapi.binance.com/fapi/v1/exchangeInfo"


def _detailed(symbol: str = "BTCUSDT") -> dict[str, object]:
    return {
        "accepted": True,
        "blocking": False,
        "symbol": symbol,
        "membership_class": membership.MEMBERSHIP_ACCEPTED_CLASS,
        "in_archive": True,
        "in_current_exchange": True,
        "evidence": [
            {
                "symbol": symbol,
                "kind": "authenticated_current_exchange_info",
                "endpoint": ENDPOINT,
                "response_sha256": DIGEST,
                "contract_type": "PERPETUAL",
                "status": "TRADING",
                "underlying_type": "COIN",
                "base_asset": symbol,
                "quote_asset": "USDT",
                "margin_asset": "USDT",
                "pair": symbol,
                "onboard_ms": 1_700_000_000_000,
                "delivery_ms": 4_133_404_800_000,
                "closed_observed_ms": None,
                "semantics_state": "supported",
            }
        ],
    }


def _funding(symbol: str = "ODD_NATIVE") -> dict[str, object]:
    return {
        "accepted": True,
        "blocking": False,
        "symbol": symbol,
        "membership_class": membership.MEMBERSHIP_ACCEPTED_CLASS,
        "in_archive": True,
        "in_current_exchange": False,
        "evidence": [
            {
                "kind": membership.FUNDING_ONLY_EVIDENCE_CLASS,
                "semantics": membership.FUNDING_ONLY_SEMANTICS,
                "families": ["monthly/fundingRate"],
                "example_key": (
                    f"data/futures/um/monthly/fundingRate/{symbol}/"
                    f"{symbol}-fundingRate-2021-01.zip"
                ),
            }
        ],
    }


def _excluded(symbol: str = "BTCUSDT_210326") -> dict[str, object]:
    return {
        "accepted": False,
        "blocking": False,
        "symbol": symbol,
        "membership_class": "delivery_non_perpetual",
        "in_archive": True,
        "in_current_exchange": False,
        "evidence": [{"kind": "reviewed_archive_delivery_inference"}],
    }


def _documents(
    classifications: list[dict[str, object]] | None = None,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    rows = classifications or [_detailed(), _funding(), _excluded()]
    detailed_symbols = [
        str(row["symbol"])
        for row in rows
        if row.get("accepted") is True
        and row.get("evidence")
        and row["evidence"][0].get("kind") == "authenticated_current_exchange_info"
    ]
    accepted = sum(row.get("accepted") is True for row in rows)
    report = {
        "membership": {
            "resolved": True,
            "unresolved_count": 0,
            "unresolved_symbols": [],
            "confirmed_count": accepted,
            "classifications": rows,
        }
    }
    metadata = {"symbol_snapshot": {symbol: DIGEST for symbol in detailed_symbols}}
    sizing = {
        "authority": {
            "bindings": {
                "report_sha256": membership.REPORT_SHA256,
                "contract_metadata_sha256": membership.METADATA_SHA256,
            }
        },
        "code_identity": {
            "policy_identity": membership.SIZING_POLICY_IDENTITY,
            "writer_identity": membership.writer_identity(),
        },
        "projections": {
            "final_product_schemas": {
                membership.PRODUCT: membership._schema_contract()
            },
            "fixed_schema_products": {
                membership.PRODUCT: {
                    "projected_rows": membership.ACCEPTED_MEMBERSHIP_IDENTITIES,
                    "partition_count": membership.ACCEPTED_MEMBERSHIP_IDENTITIES,
                    "projected_bytes": membership.EXPECTED_PROJECTED_BYTES,
                }
            },
        },
    }
    return report, metadata, sizing


def _normalize(
    tmp_path: Path,
    classifications: list[dict[str, object]] | None = None,
    *,
    hooks: membership.PublicationHooks = membership.PublicationHooks(),
) -> membership.MembershipNormalizationResult:
    report, metadata, sizing = _documents(classifications)
    return membership.normalize_membership_documents(
        report, metadata, sizing, tmp_path / ".membership", hooks=hooks
    )


def _completion(result: membership.MembershipNormalizationResult) -> dict[str, object]:
    return json.loads(result.completion_path.read_text())


def test_exact_24_column_schema_and_native_reference_identity(tmp_path: Path) -> None:
    result = _normalize(tmp_path)
    assert len(membership.SCHEMA) == 24
    assert membership.SCHEMA.names == [
        "venue",
        "native_symbol",
        "canonical_instrument_id",
        "canonical_instrument_version_id",
        "reference_identity_state",
        "membership_class",
        "contract_type",
        "contract_metadata_state",
        "contract_evidence_class",
        "contract_evidence_source",
        "contract_status",
        "underlying_type",
        "base_asset",
        "quote_asset",
        "margin_asset",
        "pair",
        "in_archive",
        "in_current_exchange",
        "onboard_ms",
        "delivery_ms",
        "closed_observed_ms",
        "semantics_state",
        "contract_snapshot_sha256",
        "evidence_records",
    ]
    table = pq.read_table(result.partitions[0].parquet_path)
    assert table.schema == membership.SCHEMA
    assert table.column("canonical_instrument_id").to_pylist() == [None]
    assert table.column("canonical_instrument_version_id").to_pylist() == [None]
    assert table.column("reference_identity_state").to_pylist() == [
        "reference_identity_not_yet_created"
    ]


def test_only_accepted_confirmed_perpetual_classifications_are_rows(
    tmp_path: Path,
) -> None:
    result = _normalize(tmp_path)
    assert [item.native_symbol for item in result.partitions] == [
        "BTCUSDT",
        "ODD_NATIVE",
    ]
    complete = _completion(result)
    assert complete["row_equation"] == {
        "classifications": 3,
        "accepted_membership_rows": 2,
        "excluded_classifications": 1,
    }
    assert complete["metadata_equation"] == {
        "accepted_membership_rows": 2,
        "detailed_metadata_rows": 1,
        "funding_only_rows": 1,
    }


def test_full_corpus_contract_is_exact_1008_771_237_and_698_73() -> None:
    rows = [_detailed(f"DETAIL{index}") for index in range(698)]
    rows.extend(_funding(f"FUND{index}") for index in range(73))
    rows.extend(_excluded(f"EXCLUDED{index}") for index in range(237))
    report, metadata, _sizing = _documents(rows)
    accepted, excluded = membership.build_membership_rows(
        report, metadata, enforce_full_corpus=True
    )
    assert len(rows) == 1_008
    assert len(accepted) == 771
    assert len(excluded) == 237
    assert sum(
        row["contract_metadata_state"] == membership.MEMBERSHIP_DETAILED_STATE
        for row in accepted
    ) == 698
    assert sum(
        row["contract_metadata_state"]
        == membership.MEMBERSHIP_FUNDING_ONLY_STATE
        for row in accepted
    ) == 73


def test_funding_only_proves_perpetual_and_keeps_all_ticker_terms_null(
    tmp_path: Path,
) -> None:
    result = _normalize(tmp_path, [_funding("NOT_A_SUFFIX_CONTRACT")])
    table = pq.read_table(result.partitions[0].parquet_path)
    row = table.to_pylist()[0]
    assert row["native_symbol"] == "NOT_A_SUFFIX_CONTRACT"
    assert row["contract_type"] == "PERPETUAL"
    assert row["semantics_state"] == membership.FUNDING_ONLY_SEMANTICS
    assert all(row[field] is None for field in membership._FUNDING_NULL_FIELDS)
    assert row["canonical_instrument_id"] is None
    assert row["canonical_instrument_version_id"] is None


def test_conflicting_stable_evidence_fails_closed(tmp_path: Path) -> None:
    row = _detailed()
    conflict = deepcopy(row["evidence"][0])
    conflict["quote_asset"] = "USDC"
    row["evidence"].append(conflict)
    with pytest.raises(
        membership.MembershipNormalizationError, match="conflicts on a stable fact"
    ):
        _normalize(tmp_path, [row])


@pytest.mark.parametrize(
    "mutation,message",
    [
        (lambda row: row.update(evidence=[]), "no evidence"),
        (lambda row: row.update(membership_class="other"), "class changed"),
        (lambda row: row.update(blocking=True), "is blocking"),
    ],
)
def test_missing_or_unaccepted_membership_evidence_fails_closed(
    tmp_path: Path, mutation, message: str
) -> None:
    row = _detailed()
    mutation(row)
    with pytest.raises(membership.MembershipNormalizationError, match=message):
        _normalize(tmp_path, [row])


def test_unresolved_membership_and_duplicate_symbols_fail_closed(tmp_path: Path) -> None:
    report, metadata, _sizing = _documents([_detailed()])
    report["membership"]["resolved"] = False
    with pytest.raises(membership.MembershipNormalizationError, match="unresolved"):
        membership.build_membership_rows(report, metadata, enforce_full_corpus=False)
    with pytest.raises(membership.MembershipNormalizationError, match="repeats a symbol"):
        _normalize(tmp_path, [_detailed(), _detailed()])


def test_distinct_response_and_contract_snapshot_hashes_are_preserved(
    tmp_path: Path,
) -> None:
    report, metadata, sizing = _documents([_detailed()])
    metadata["symbol_snapshot"]["BTCUSDT"] = "b" * 64
    result = membership.normalize_membership_documents(
        report, metadata, sizing, tmp_path / ".membership"
    )
    row = pq.read_table(result.partitions[0].parquet_path).to_pylist()[0]
    assert report["membership"]["classifications"][0]["evidence"][0][
        "response_sha256"
    ] == DIGEST
    assert row["contract_snapshot_sha256"] == "b" * 64


@pytest.mark.parametrize("snapshot", [None, "B" * 64, "b" * 63, "not-a-digest"])
def test_missing_or_malformed_contract_snapshot_fails_closed(
    tmp_path: Path, snapshot: str | None
) -> None:
    report, metadata, sizing = _documents([_detailed()])
    if snapshot is None:
        metadata["symbol_snapshot"].pop("BTCUSDT")
    else:
        metadata["symbol_snapshot"]["BTCUSDT"] = snapshot
    with pytest.raises(
        membership.MembershipNormalizationError, match="no contract snapshot"
    ):
        membership.normalize_membership_documents(
            report, metadata, sizing, tmp_path / ".membership"
        )


def test_funding_only_cannot_gain_metadata_or_inferred_terms(tmp_path: Path) -> None:
    report, metadata, sizing = _documents([_funding("ODD_NATIVE")])
    metadata["symbol_snapshot"]["ODD_NATIVE"] = DIGEST
    with pytest.raises(membership.MembershipNormalizationError, match="unexpectedly has"):
        membership.normalize_membership_documents(
            report, metadata, sizing, tmp_path / ".membership"
        )


def test_sizing_schema_writer_policy_counts_and_bindings_are_pinned(
    tmp_path: Path,
) -> None:
    report, metadata, sizing = _documents([_detailed()])
    cases = [
        ("schema", lambda value: value["projections"]["final_product_schemas"][membership.PRODUCT].pop()),
        ("writer", lambda value: value["code_identity"].update(writer_identity="changed")),
        ("policy", lambda value: value["code_identity"].update(policy_identity="changed")),
        ("projected rows", lambda value: value["projections"]["fixed_schema_products"][membership.PRODUCT].update(projected_rows=770)),
        ("report binding", lambda value: value["authority"]["bindings"].update(report_sha256="b" * 64)),
    ]
    for message, mutate in cases:
        candidate = deepcopy(sizing)
        mutate(candidate)
        with pytest.raises(membership.MembershipNormalizationError, match=message):
            membership.normalize_membership_documents(
                report, metadata, candidate, tmp_path / f".{message.replace(' ', '-')}"
            )


def test_exact_input_identities_are_constants_and_tamper_is_rejected(
    tmp_path: Path,
) -> None:
    assert membership.REPORT_SHA256 == (
        "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
    )
    assert membership.METADATA_SHA256 == (
        "7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42"
    )
    assert membership.SIZING_SHA256 == (
        "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589"
    )
    authority = tmp_path / "authority.json"
    authority.write_text("{}\n")
    with pytest.raises(membership.MembershipNormalizationError, match="digest changed"):
        membership._read_pinned_json(authority, "0" * 64, 1024)


def test_authority_and_output_symlinks_are_rejected(tmp_path: Path) -> None:
    authority = tmp_path / "authority.json"
    authority.write_text("{}\n")
    link = tmp_path / "authority-link.json"
    link.symlink_to(authority)
    with pytest.raises(membership.MembershipNormalizationError, match="symlink"):
        membership._read_pinned_json(link, hashlib.sha256(b"{}\n").hexdigest(), 1024)
    output_target = tmp_path / ".target"
    output_target.mkdir()
    output_link = tmp_path / ".membership"
    output_link.symlink_to(output_target, target_is_directory=True)
    with pytest.raises(membership.MembershipNormalizationError, match="symlink"):
        _normalize(tmp_path)


@pytest.mark.parametrize("symbol", ["../escape", "bad/name", "bad\\name", "", "."])
def test_unsafe_native_symbol_paths_are_rejected(tmp_path: Path, symbol: str) -> None:
    with pytest.raises(membership.MembershipNormalizationError, match="safe output"):
        _normalize(tmp_path, [_funding(symbol)])


def test_completion_is_last_and_interruption_remains_invisible(tmp_path: Path) -> None:
    observed: list[str] = []

    def interrupt(kind: str, _stage: Path, _destination: Path) -> None:
        observed.append(kind)
        if kind == "completion":
            raise RuntimeError("stop-before-completion")

    with pytest.raises(RuntimeError, match="stop-before-completion"):
        _normalize(
            tmp_path,
            hooks=membership.PublicationHooks(before_publish=interrupt),
        )
    assert observed[-1] == "completion"
    completed = tmp_path / ".membership" / ".complete"
    assert not completed.exists() or not list(completed.iterdir())


def test_replay_reuses_byte_identical_partitions_and_completion(tmp_path: Path) -> None:
    first = _normalize(tmp_path)
    first_bytes = {
        path.relative_to(tmp_path / ".membership"): path.read_bytes()
        for item in first.partitions
        for path in (item.parquet_path, item.lineage_path)
    }
    first_bytes[first.completion_path.relative_to(tmp_path / ".membership")] = (
        first.completion_path.read_bytes()
    )
    second = _normalize(tmp_path)
    assert second.completion_sha256 == first.completion_sha256
    assert second.completion_reused is True
    assert all(item.reused for item in second.partitions)
    assert all(
        (tmp_path / ".membership" / relative).read_bytes() == body
        for relative, body in first_bytes.items()
    )


def test_existing_content_address_is_never_clobbered(tmp_path: Path) -> None:
    first = _normalize(tmp_path)
    victim = first.partitions[0].parquet_path
    victim.write_bytes(b"tampered")
    with pytest.raises(
        membership.MembershipNormalizationError,
        match="replay differs|published membership Parquet",
    ):
        _normalize(tmp_path)
    assert victim.read_bytes() == b"tampered"


def test_lineage_and_completion_bind_all_three_authorities(tmp_path: Path) -> None:
    result = _normalize(tmp_path)
    expected = {
        "report": membership.REPORT_SHA256,
        "contract_metadata": membership.METADATA_SHA256,
        "sizing": membership.SIZING_SHA256,
    }
    complete = _completion(result)
    lineage = json.loads(result.partitions[0].lineage_path.read_text())
    assert complete["authority_sha256"] == expected
    assert lineage["authority_sha256"] == expected
    assert lineage["classification_sha256"]
    assert complete["partitions"][0]["lineage_sha256"] == result.partitions[0].lineage_sha256
