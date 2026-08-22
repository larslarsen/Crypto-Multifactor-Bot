"""CEX-002 ADR-0021 — prove the bounded real-sample storage sizing contract.

The fixtures reproduce the accepted evidence *shapes*: a ten-family manifest detail, a
separate two-family cost manifest resolved through retained listing responses, and
report-bound Coinalyze provenance in a content-addressed cache whose files carry no
extension. The pinned production identities and totals cannot be reproduced at fixture
scale, so they are re-pointed per fixture; one test asserts the literal review-179/181
values on their own.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from cryptofactors.acquisition import binance_usdm_harmonic_sizing as sizing
from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    KNOWN_ARCHIVE_SCHEMAS,
    persist_provider_sidecar,
)
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    ARCHIVE_FAMILIES,
    CATALOG_PAGE_BYTES,
    COST_FAMILIES,
    MINIMUM_OPERATING_RESERVE_BYTES,
    OUTPUT_MULTIPLICITY,
    PHYSICAL_FAMILIES,
    SIZING_ROW_BATCH,
    STATE_BLOCKED,
    STATE_SUFFICIENT,
    AuthorityPaths,
    CohortSample,
    PhysicalObject,
    SizingError,
    ceil_div,
    coinalyze_lifecycles,
    coinalyze_symbol_sets,
    derive_sample_cohort,
    envelope_schema,
    family_coefficients,
    group_objects,
    load_sizing_authority,
    measure_liquidation_response,
    measure_sample_envelope,
    operating_reserve_bytes,
    project_coinalyze,
    project_families,
    publish_sizing_envelope,
    publish_sizing_receipt,
    ratio_exceeds,
    reconcile_physical_inputs,
    resolve_coinalyze_evidence,
    resolve_cost_objects,
    resolve_selected_objects,
    run_storage_sizing,
    verify_retained_sample,
    write_liquidation_envelope,
)

_TOKENS: dict[str, tuple[str, ...]] = {
    "klines": (
        "1577836800000", "1.0", "2.0", "0.5", "1.5", "10", "1577840399999",
        "15.0", "7", "4.0", "6.0", "0",
    ),
    "metrics": ("2020-01-01 00:00:00", "BTCUSDT", "1", "2", "3", "4", "5", "6"),
    "premiumIndexKlines": (
        "1577836800000", "1.0", "2.0", "0.5", "1.5", "10", "1577840399999",
        "15.0", "7", "4.0", "6.0", "0",
    ),
    "markPriceKlines": (
        "1577836800000", "1.0", "2.0", "0.5", "1.5", "10", "1577840399999",
        "15.0", "7", "4.0", "6.0", "0",
    ),
    "indexPriceKlines": (
        "1577836800000", "1.0", "2.0", "0.5", "1.5", "10", "1577840399999",
        "15.0", "7", "4.0", "6.0", "0",
    ),
    "bookTicker": ("1", "100.0", "2.0", "100.5", "3.0", "1577836800000", "1577836800001"),
    "bookDepth": ("1577836800000", "1", "5.0", "500.0"),
    "fundingRate": ("1577836800000", "8", "0.0001"),
}
_ONBOARD_MS = int(datetime(2020, 1, 1, tzinfo=UTC).timestamp() * 1000)
_CUTOFF = "2020-03-31T00:00:00+00:00"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _hint(family: str) -> str:
    return family.partition("/")[2]


def _csv(family: str, rows: int, *, headed: bool = False) -> bytes:
    tokens = _TOKENS[_hint(family)]
    lines: list[str] = []
    if headed:
        lines.append(",".join(KNOWN_ARCHIVE_SCHEMAS[_hint(family)]["headerless"]))
    lines.extend(",".join(tokens) for _ in range(rows))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _zip(name: str, payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as handle:
        handle.writestr(name, payload)
    return buffer.getvalue()


def _key(family: str, symbol: str, interval: str) -> str:
    cadence, _, hint = family.partition("/")
    return f"data/futures/um/{cadence}/{hint}/{symbol}/{symbol}-{hint}-{interval}.zip"


def _listing_xml(objects: list[tuple[str, int]]) -> bytes:
    rows = "".join(
        f"<Contents><Key>{key}</Key><Size>{size}</Size>"
        f"<ETag>&quot;{index:032x}&quot;</ETag></Contents>"
        for index, (key, size) in enumerate(objects)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<IsTruncated>false</IsTruncated>{rows}</ListBucketResult>"
    ).encode("utf-8")


def _liquidation_body(symbols: list[str], points: int) -> bytes:
    return json.dumps(
        [
            {
                "symbol": symbol,
                "history": [
                    {"t": 1577836800 + index * 86_400, "l": "1.5", "s": "2.5"}
                    for index in range(points)
                ],
            }
            for symbol in symbols
        ]
    ).encode("utf-8")


@pytest.fixture()
def accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A store shaped like the accepted one: 10-family manifest plus cost/listing."""
    store = tmp_path / "store"
    raw = store / "raw" / "sha256"
    listing_cache = store / "list_cache"
    coinalyze_cache = store / "coinalyze_cache"
    for directory in (raw, listing_cache, coinalyze_cache):
        directory.mkdir(parents=True)

    symbols = ("BTCUSDT", "ETHUSDT")
    intervals = ("2020-01-01", "2020-01-02", "2020-02-01")
    selected_rows: list[dict[str, Any]] = []
    for family in ARCHIVE_FAMILIES:
        for symbol in symbols:
            for interval in intervals:
                key = _key(family, symbol, interval)
                selected_rows.append(
                    {
                        "family": family,
                        "symbol": symbol,
                        "key": key,
                        "economic_interval": interval,
                        "byte_size": 1_000 + len(key),
                        # Only a few manifest rows are already consumable: that set, not
                        # the sizing cohort, is the acquisition credit.
                        "consumable": family == "daily/klines" and interval != "2020-02-01",
                    }
                )
    cost_rows: list[dict[str, Any]] = []
    for family in COST_FAMILIES:
        for symbol in symbols:
            for interval in intervals:
                key = _key(family, symbol, interval)
                cost_rows.append(
                    {
                        "family": family,
                        "symbol": symbol,
                        "key": key,
                        "economic_interval": interval,
                        "byte_size": 2_000 + len(key),
                    }
                )

    detail_path = store / "manifest_detail.jsonl.gz"
    with gzip.open(detail_path, "wb", compresslevel=9, mtime=0) as handle:
        for row in selected_rows:
            handle.write(
                (json.dumps({"record_type": "row", "record": row}, sort_keys=True) + "\n").encode()
            )
    detail_bytes = detail_path.read_bytes()
    with gzip.open(detail_path, "rb") as handle:
        expanded = handle.read()

    listing_body = _listing_xml([(row["key"], row["byte_size"]) for row in cost_rows])
    listing_digest = _sha256(listing_body)
    (listing_cache / listing_digest).write_bytes(listing_body)

    plan_entries: list[dict[str, Any]] = []
    checkpoint_objects: dict[str, dict[str, Any]] = {}
    cohort_rows = selected_rows[:10] + cost_rows[:2]
    credit_rows = [row for row in selected_rows if row["consumable"]]
    assert credit_rows and len(credit_rows) != len(cohort_rows)
    for index, row in enumerate(cohort_rows + credit_rows):
        family = str(row["family"])
        payload = _zip("data.csv", _csv(family, 3 + index % 4))
        digest = _sha256(payload)
        (raw / digest).write_bytes(payload)
        sidecar_body = f"{digest}  {row['key'].rsplit('/', 1)[-1]}\n".encode()
        sidecar_path, sidecar_digest = persist_provider_sidecar(
            sidecar_body, sidecar_dir=listing_cache
        )
        url = f"https://data.binance.vision/{row['key']}"
        checkpoint_objects[str(row["key"])] = {
            "status": "complete",
            "sha256": digest,
            "byte_size": len(payload),
            "url": url,
            "provider_checksum": digest,
            "checksum_match": True,
            "schema_kind": "headerless",
            "schema_fields": list(KNOWN_ARCHIVE_SCHEMAS[_hint(family)]["headerless"]),
            "provider_checksum_path": str(sidecar_path),
            "provider_checksum_sha256": sidecar_digest,
        }
        if index < len(cohort_rows):
            plan_entries.append(
                {
                    "family": family,
                    "symbol": row["symbol"],
                    "key": row["key"],
                    "url": url,
                    "action": "download" if index % 2 else "reuse_retained",
                    "byte_size": len(payload),
                }
            )
    aliases = [dict(plan_entries[0], action="alias"), dict(plan_entries[1], action="alias")]
    plan_entries.extend(aliases)

    inventory_body = json.dumps(
        [{"symbol": f"SYM{index}_PERP.A"} for index in range(4)]
    ).encode("utf-8")
    # The accepted shape: one retained request whose single response carries two symbols.
    liquidation_body = _liquidation_body(["SYM0_PERP.A", "SYM1_PERP.A"], 5)
    provenance: list[dict[str, Any]] = []
    for endpoint, body in (
        ("/future-markets", inventory_body),
        ("/liquidation-history", liquidation_body),
        ("/open-interest-history", b"[]"),
        ("/funding-rate-history", b"[]"),
        ("/ohlcv-history", b"[]"),
    ):
        digest = _sha256(body)
        (coinalyze_cache / digest).write_bytes(body)
        provenance.append(
            {
                "path": endpoint,
                "params": {"symbols": "BTCUSDT_PERP.A", "api_key": "<redacted>"}
                if False
                else {"symbols": "BTCUSDT_PERP.A"},
                "sha256": digest,
                "byte_size": len(body),
                "content_path": str(coinalyze_cache / digest),
            }
        )

    supported = [f"SYM{index}_PERP.A" for index in range(4)]
    unmapped = ["GAPUSDT"]
    inputs = {
        "inventory_digest": "a" * 64,
        "listing_digest": "b" * 64,
        "membership_digest": "c" * 64,
        "code_config_digest": "d" * 64,
        "budget_digest": "e" * 64,
        "retained_digest": "f" * 64,
    }
    binding = {
        "migration_id": "cex002_reviewed_v4_migration",
        "source_receipts": [
            {
                "prepared_at": "2026-08-21T00:00:00+00:00",
                "source_identity": {
                    "code_config_digest": inputs["code_config_digest"],
                    "module_sha256": "",
                },
            }
        ],
    }
    source_path = tmp_path / "qualification.py"
    cli_path = tmp_path / "qualify_cli.py"
    source_path.write_text("# accepted qualification source\n")
    cli_path.write_text("# accepted qualification cli\n")
    binding["source_receipts"][0]["source_identity"]["module_sha256"] = _sha256(
        source_path.read_bytes()
    )
    lock = {
        "ticket": "CEX-002",
        "kind": "sample_plan_lock",
        "plan_version": 4,
        "plan_digest": "9" * 64,
        "inputs": inputs,
        "plan": {"entries": plan_entries},
        "budget_snapshot": {"amendment_binding": binding},
        "history": [],
    }
    ledger = {"ticket": "CEX-002", "kind": "budget_ledger", "binding": binding}
    progress = {"ticket": "CEX-002", "kind": "sample_checkpoint", "objects": checkpoint_objects}
    listing_checkpoint = {
        "ticket": "CEX-002",
        "kind": "listing_checkpoint",
        "entries": {
            "listing:cost": {
                "response_sha256": listing_digest,
                "content_path": str(listing_cache / listing_digest),
                "byte_size": len(listing_body),
            }
        },
    }
    metadata = {
        "ticket": "CEX-002",
        "symbol_snapshot": {
            f"SYM{index}": {"onboard_ms": _ONBOARD_MS, "close_ms": None} for index in range(4)
        },
    }
    report = {
        "generated_at": _CUTOFF,
        "plan_lock": {"plan_version": 4, "plan_digest": "9" * 64, "inputs": inputs},
        "storage": {"cost_sample": {"keys": [row["key"] for row in cost_rows]}},
        "acquisition_manifest": {
            "detail": {
                "compressed_sha256": _sha256(detail_bytes),
                "uncompressed_sha256": _sha256(expanded),
                "uncompressed_bytes": len(expanded),
            }
        },
        "membership": {
            "classifications": [
                {"symbol": "BTCUSDT", "accepted": True},
                {"symbol": "ETHUSDT", "accepted": True},
                {"symbol": "GAPUSDT", "accepted": True},
            ]
        },
        "coinalyze": {
            "provenance": provenance,
            "universe_support": {
                "supported_symbols": supported,
                "unmapped_symbols": unmapped,
                "supported_count": len(supported),
                "unmapped_count": len(unmapped),
            },
        },
    }
    paths = {
        "lock": store / "cex002_sample_plan_lock.json",
        "ledger": store / "cex002_amendment_ledger.json",
        "progress": store / "cex002_qualification_progress.json",
        "listing": store / "cex002_listing_checkpoint.json",
        "metadata": store / "cex002_official_contract_metadata.json",
        "report": store / "62_report.json",
    }
    for name, document in (
        ("lock", lock),
        ("ledger", ledger),
        ("progress", progress),
        ("listing", listing_checkpoint),
        ("metadata", metadata),
        ("report", report),
    ):
        paths[name].write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")

    pins = {
        "ACCEPTED_REPORT_SHA256": _sha256(paths["report"].read_bytes()),
        "ACCEPTED_REPORT_BYTES": paths["report"].stat().st_size,
        "ACCEPTED_MANIFEST_DETAIL_SHA256": _sha256(detail_bytes),
        "ACCEPTED_MANIFEST_DETAIL_BYTES": len(detail_bytes),
        "ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_SHA256": _sha256(expanded),
        "ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_BYTES": len(expanded),
        "ACCEPTED_LOCK_SHA256": _sha256(paths["lock"].read_bytes()),
        "ACCEPTED_AMENDMENT_LEDGER_SHA256": _sha256(paths["ledger"].read_bytes()),
        "ACCEPTED_QUALIFICATION_SOURCE_SHA256": _sha256(source_path.read_bytes()),
        "ACCEPTED_QUALIFICATION_CLI_SHA256": _sha256(cli_path.read_bytes()),
        "ACCEPTED_PROGRESS_CHECKPOINT_SHA256": _sha256(paths["progress"].read_bytes()),
        "ACCEPTED_LISTING_CHECKPOINT_SHA256": _sha256(paths["listing"].read_bytes()),
        "ACCEPTED_CONTRACT_METADATA_SHA256": _sha256(paths["metadata"].read_bytes()),
        "ACCEPTED_PLAN_ENTRIES": len(plan_entries),
        "ACCEPTED_PLAN_ACTIONS": {
            "download": sum(1 for item in plan_entries if item["action"] == "download"),
            "reuse_retained": sum(
                1 for item in plan_entries if item["action"] == "reuse_retained"
            ),
            "alias": sum(1 for item in plan_entries if item["action"] == "alias"),
        },
        "ACCEPTED_SAMPLE_COHORT": len(cohort_rows),
        "ACCEPTED_SELECTED_OBJECTS": len(selected_rows),
        "ACCEPTED_SELECTED_BYTES": sum(int(row["byte_size"]) for row in selected_rows),
        "ACCEPTED_COST_OBJECTS": len(cost_rows),
        "ACCEPTED_COST_BYTES": sum(int(row["byte_size"]) for row in cost_rows),
        "ACCEPTED_COMBINED_OBJECTS": len(selected_rows) + len(cost_rows),
        "ACCEPTED_COMBINED_BYTES": sum(
            int(row["byte_size"]) for row in selected_rows + cost_rows
        ),
        "ACCEPTED_RETAINED_CREDIT_OBJECTS": len(credit_rows),
        "ACCEPTED_RETAINED_CREDIT_BYTES": sum(
            int(checkpoint_objects[str(row["key"])]["byte_size"]) for row in credit_rows
        ),
        "ACCEPTED_COINALYZE_SUPPORTED_MAPPINGS": len(supported),
        "ACCEPTED_COINALYZE_TYPED_GAPS": len(unmapped),
    }
    pins["ACCEPTED_NEW_BINANCE_RAW_BYTES"] = (
        pins["ACCEPTED_COMBINED_BYTES"] - pins["ACCEPTED_RETAINED_CREDIT_BYTES"]
    )
    for name, value in pins.items():
        monkeypatch.setattr(sizing, name, value)

    authority_paths = AuthorityPaths(
        store_root=store,
        report_path=paths["report"],
        manifest_detail_path=detail_path,
        qualification_source_path=source_path,
        qualification_cli_path=cli_path,
        lock_path=paths["lock"],
        amendment_ledger_path=paths["ledger"],
        progress_checkpoint_path=paths["progress"],
        listing_checkpoint_path=paths["listing"],
        contract_metadata_path=paths["metadata"],
        listing_cache_dir=listing_cache,
        coinalyze_cache_dir=coinalyze_cache,
        sample_dir=raw,
        sidecar_dir=listing_cache,
    )
    return {
        "paths": authority_paths,
        "files": paths,
        "detail_path": detail_path,
        "store": store,
        "selected_rows": selected_rows,
        "cost_rows": cost_rows,
        "plan_entries": plan_entries,
        "listing_cache": listing_cache,
        "coinalyze_cache": coinalyze_cache,
        "supported": supported,
        "unmapped": unmapped,
        "cohort_rows": cohort_rows,
        "credit_rows": credit_rows,
        "pins": pins,
    }


def test_pinned_review179_and_181_identities_are_literal() -> None:
    import importlib

    fresh = importlib.reload(sizing)
    assert fresh.ACCEPTED_REPORT_BYTES == 13_559_766
    assert fresh.ACCEPTED_MANIFEST_DETAIL_BYTES == 11_294_610
    assert fresh.ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_BYTES == 466_713_055
    assert fresh.ACCEPTED_PROGRESS_CHECKPOINT_SHA256 == (
        "cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff"
    )
    assert fresh.ACCEPTED_LISTING_CHECKPOINT_SHA256 == (
        "d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a"
    )
    assert fresh.ACCEPTED_CONTRACT_METADATA_SHA256 == (
        "e520f0f072730f566d027342ddc7e09f7b690ab80e76acbd40756759f13add1f"
    )
    # The exact accepted physical requirement, and its two separate authorities.
    assert fresh.ACCEPTED_SELECTED_OBJECTS == 733_203
    assert fresh.ACCEPTED_SELECTED_BYTES == 7_833_966_625
    assert fresh.ACCEPTED_COST_OBJECTS == 3_144
    assert fresh.ACCEPTED_COST_BYTES == 12_522_974_218
    assert fresh.ACCEPTED_COMBINED_OBJECTS == 736_347
    assert fresh.ACCEPTED_COMBINED_BYTES == 20_356_940_843
    assert fresh.ACCEPTED_RETAINED_CREDIT_OBJECTS == 73
    assert fresh.ACCEPTED_RETAINED_CREDIT_BYTES == 5_225_416
    assert fresh.ACCEPTED_NEW_BINANCE_RAW_BYTES == 20_351_715_427
    assert (
        fresh.ACCEPTED_COMBINED_BYTES - fresh.ACCEPTED_RETAINED_CREDIT_BYTES
        == fresh.ACCEPTED_NEW_BINANCE_RAW_BYTES
    )
    assert fresh.ACCEPTED_PLAN_ACTIONS == {
        "download": 84,
        "reuse_retained": 12,
        "alias": 10,
    }
    assert sum(fresh.ACCEPTED_PLAN_ACTIONS.values()) == fresh.ACCEPTED_PLAN_ENTRIES == 106
    assert fresh.ACCEPTED_SAMPLE_COHORT == 96
    assert len(fresh.ARCHIVE_FAMILIES) == 10
    assert len(fresh.COST_FAMILIES) == 2
    assert len(fresh.PHYSICAL_FAMILIES) == 12
    assert fresh.ACCEPTED_COINALYZE_SUPPORTED_MAPPINGS == 569
    assert fresh.ACCEPTED_COINALYZE_TYPED_GAPS == 202
    assert fresh.ACCEPTED_COINALYZE_PROVENANCE_RECORDS == 5


def test_accepted_authority_loads_with_every_new_pin(accepted: dict[str, Any]) -> None:
    authority = load_sizing_authority(accepted["paths"])
    assert authority.bindings["progress_checkpoint_sha256"]
    assert authority.bindings["listing_checkpoint_sha256"]
    assert authority.bindings["contract_metadata_sha256"]
    assert len(authority.plan_entries) == len(accepted["plan_entries"])


@pytest.mark.parametrize(
    "target", ["report", "lock", "ledger", "progress", "listing", "metadata"]
)
def test_each_pinned_artifact_failure_blocks(
    accepted: dict[str, Any], target: str
) -> None:
    path = accepted["files"][target]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(SizingError):
        load_sizing_authority(accepted["paths"])


def test_selected_rows_are_the_ten_archive_families(accepted: dict[str, Any]) -> None:
    objects, counts = resolve_selected_objects(accepted["detail_path"])
    assert {item.family for item in objects} == set(ARCHIVE_FAMILIES)
    assert not {item.family for item in objects} & set(COST_FAMILIES)
    assert counts["row_count"] == len(accepted["selected_rows"])
    assert counts["selected_bytes"] == sizing.ACCEPTED_SELECTED_BYTES


def test_cost_keys_resolve_through_retained_listing_evidence(
    accepted: dict[str, Any]
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    objects, counts = resolve_cost_objects(
        authority, listing_cache_dir=accepted["listing_cache"]
    )
    assert {item.family for item in objects} == set(COST_FAMILIES)
    assert counts["cost_object_count"] == len(accepted["cost_rows"])
    assert counts["cost_bytes"] == sizing.ACCEPTED_COST_BYTES
    assert counts["listing_responses_used"] == 1
    assert all(item.byte_size > 0 for item in objects)


def test_a_cost_key_without_listing_evidence_blocks(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    monkeypatch.setattr(sizing, "ACCEPTED_COST_OBJECTS", len(accepted["cost_rows"]) + 1)
    report = json.loads(accepted["files"]["report"].read_text())
    report["storage"]["cost_sample"]["keys"].append(
        _key("daily/bookTicker", "BTCUSDT", "2099-01-01")
    )
    accepted["files"]["report"].write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    monkeypatch.setattr(
        sizing, "ACCEPTED_REPORT_SHA256", _sha256(accepted["files"]["report"].read_bytes())
    )
    monkeypatch.setattr(
        sizing, "ACCEPTED_REPORT_BYTES", accepted["files"]["report"].stat().st_size
    )
    authority = load_sizing_authority(accepted["paths"])
    # Nothing is inferred or downloaded: an unsized cost key blocks.
    with pytest.raises(SizingError, match="does not size every cost key"):
        resolve_cost_objects(authority, listing_cache_dir=accepted["listing_cache"])


def test_exact_totals_reconcile_before_measurement(accepted: dict[str, Any]) -> None:
    authority = load_sizing_authority(accepted["paths"])
    selected, _ = resolve_selected_objects(accepted["detail_path"])
    cost, _ = resolve_cost_objects(authority, listing_cache_dir=accepted["listing_cache"])
    checkpoint = json.loads(accepted["files"]["progress"].read_text())["objects"]
    credit = sizing.prove_retained_acquisition_credit(
        selected,
        checkpoint=checkpoint,
        sample_dir=accepted["paths"].sample_dir,
        sidecar_dir=accepted["paths"].sidecar_dir,
    )
    # The credit is the manifest's consumable coverage, not the measurement cohort.
    assert credit["objects"] == len(accepted["credit_rows"])
    assert credit["objects"] != len(accepted["cohort_rows"])
    assert credit["bytes"] == sizing.ACCEPTED_RETAINED_CREDIT_BYTES
    reconciliation = reconcile_physical_inputs(
        selected=selected,
        cost=cost,
        retained_credit_objects=int(credit["objects"]),
        retained_credit_bytes=int(credit["bytes"]),
    )
    assert reconciliation["combined_objects"] == sizing.ACCEPTED_COMBINED_OBJECTS
    assert reconciliation["combined_bytes"] == sizing.ACCEPTED_COMBINED_BYTES
    assert (
        reconciliation["projected_new_binance_raw_bytes"]
        == sizing.ACCEPTED_NEW_BINANCE_RAW_BYTES
    )
    assert reconciliation["overlap_objects"] == 0
    with pytest.raises(SizingError):
        reconcile_physical_inputs(
            selected=selected,
            cost=cost,
            retained_credit_objects=1,
            retained_credit_bytes=sizing.ACCEPTED_RETAINED_CREDIT_BYTES,
        )


def test_plan_action_accounting_and_alias_agreement(accepted: dict[str, Any]) -> None:
    authority = load_sizing_authority(accepted["paths"])
    cohort = derive_sample_cohort(authority)
    assert len(cohort) == sizing.ACCEPTED_SAMPLE_COHORT
    assert sum(item.aliases for item in cohort) == sizing.ACCEPTED_PLAN_ACTIONS["alias"]
    assert {item.family for item in cohort} <= set(PHYSICAL_FAMILIES)


def test_an_alias_that_disagrees_blocks(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    lock = json.loads(accepted["files"]["lock"].read_text())
    for entry in lock["plan"]["entries"]:
        if entry["action"] == "alias":
            entry["byte_size"] = int(entry["byte_size"]) + 1
            break
    accepted["files"]["lock"].write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    monkeypatch.setattr(
        sizing, "ACCEPTED_LOCK_SHA256", _sha256(accepted["files"]["lock"].read_bytes())
    )
    authority = load_sizing_authority(accepted["paths"])
    with pytest.raises(SizingError, match="disagrees with the object it names"):
        derive_sample_cohort(authority)


def _cohort_sample(family: str = "daily/klines", *, interval: str = "2020-01-01") -> CohortSample:
    key = _key(family, "BTCUSDT", interval)
    return CohortSample(
        key=key,
        family=family,
        symbol="BTCUSDT",
        economic_interval=interval,
        action="reuse_retained",
        byte_size=1,
        url=f"https://data.binance.vision/{key}",
        aliases=0,
    )


@pytest.mark.parametrize("family", list(PHYSICAL_FAMILIES))
def test_every_family_measures_exact_envelope_bytes(tmp_path: Path, family: str) -> None:
    body = _csv(family, 7)
    payload = _zip("data.csv", body)
    measurement = measure_sample_envelope(
        _cohort_sample(family),
        payload=payload,
        destination=tmp_path / "a.parquet",
        schema_kind="headerless",
    )
    assert measurement.source_rows == 7
    # The exact ZIP member size, not a reconstruction from parsed tokens.
    assert measurement.extracted_member_bytes == len(body)
    assert measurement.compressed_archive_bytes == len(payload)
    assert measurement.parquet_bytes > 0
    # The footer is the real serialized metadata length; overhead is declared separately.
    assert 0 < measurement.parquet_footer_bytes < measurement.parquet_bytes
    assert measurement.parquet_file_overhead_bytes == 8 + 4
    assert measurement.pyarrow_version
    assert len(envelope_schema(family).names) == 5 + len(_TOKENS[_hint(family)])


def test_headed_input_is_measured_as_headed(tmp_path: Path) -> None:
    payload = _zip("data.csv", _csv("daily/klines", 5, headed=True))
    measurement = measure_sample_envelope(
        _cohort_sample(),
        payload=payload,
        destination=tmp_path / "a.parquet",
        schema_kind="headed",
    )
    assert measurement.schema_kind == "headed"
    assert measurement.source_rows == 5
    # A headed file whose checkpoint claims headerless is a disagreement, not a guess.
    with pytest.raises(SizingError, match="header form disagrees"):
        measure_sample_envelope(
            _cohort_sample(),
            payload=payload,
            destination=tmp_path / "b.parquet",
            schema_kind="headerless",
        )
    headerless = _zip("data.csv", _csv("daily/klines", 5))
    with pytest.raises(SizingError, match="header form disagrees"):
        measure_sample_envelope(
            _cohort_sample(),
            payload=headerless,
            destination=tmp_path / "c.parquet",
            schema_kind="headed",
        )


def test_batching_and_determinism(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _zip("data.csv", _csv("daily/bookTicker", 10))
    monkeypatch.setattr(sizing, "SIZING_ROW_BATCH", 4)
    batched = measure_sample_envelope(
        _cohort_sample("daily/bookTicker"),
        payload=payload,
        destination=tmp_path / "a.parquet",
        schema_kind="headerless",
    )
    assert batched.batches == 3
    monkeypatch.undo()
    first = measure_sample_envelope(
        _cohort_sample("daily/bookTicker"),
        payload=payload,
        destination=tmp_path / "b.parquet",
        schema_kind="headerless",
    )
    second = measure_sample_envelope(
        _cohort_sample("daily/bookTicker"),
        payload=payload,
        destination=tmp_path / "c.parquet",
        schema_kind="headerless",
    )
    assert first.parquet_sha256 == second.parquet_sha256


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"not a zip", "not a ZIP archive"),
        (_zip("a.csv", b""), "member is empty"),
        (_zip("../escape.csv", b"1\n"), "escapes its archive"),
        (_zip("/absolute.csv", b"1\n"), "absolute path"),
        (_zip("a.txt", b"1\n"), "not a CSV file"),
        (_zip("a.csv", b"1,2,3\n"), "declared schema width"),
        (_zip("a.csv", b'1,"2"x,3\n'), "not decodable CSV"),
    ],
)
def test_unsafe_or_corrupt_archives_block(
    tmp_path: Path, payload: bytes, message: str
) -> None:
    with pytest.raises(SizingError, match=message):
        measure_sample_envelope(
            _cohort_sample(),
            payload=payload,
            destination=tmp_path / "a.parquet",
            schema_kind="headerless",
        )


def test_rational_comparison_uses_cross_multiplication_beyond_float_precision() -> None:
    huge = 2**53
    # These two ratios are indistinguishable in float64 and must still order exactly.
    assert ratio_exceeds((huge + 1, huge), (huge, huge))
    assert not ratio_exceeds((huge, huge), (huge + 1, huge))
    assert ceil_div((huge + 1) * 7, 3) == ((huge + 1) * 7 + 2) // 3
    with pytest.raises(SizingError):
        ratio_exceeds((1, 0), (1, 1))
    source = Path(sizing.__file__).read_text(encoding="utf-8")
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "float(" in stripped:
            continue
        assert " / " not in stripped or "//" in stripped or '"' in stripped or "'" in stripped


def test_partitions_group_by_symbol_month_and_family() -> None:
    objects = [
        PhysicalObject(
            key=_key("daily/klines", "BTCUSDT", f"2020-01-{day:02d}"),
            family="daily/klines",
            symbol="BTCUSDT",
            economic_interval=f"2020-01-{day:02d}",
            byte_size=100,
        )
        for day in (1, 2, 3)
    ] + [
        PhysicalObject(
            key=_key("daily/klines", "BTCUSDT", "2020-02-01"),
            family="daily/klines",
            symbol="BTCUSDT",
            economic_interval="2020-02-01",
            byte_size=500,
        )
    ]
    groups = group_objects(objects)
    # Three daily objects in one month are one partition, not three.
    assert groups == {
        ("daily/klines", "BTCUSDT", "2020-01"): 300,
        ("daily/klines", "BTCUSDT", "2020-02"): 500,
    }
    projections = project_families(
        measurements=[
            sizing.EnvelopeMeasurement(
                key=f"k-{family}",
                family=family,
                symbol="BTCUSDT",
                economic_interval="2020-01-01",
                schema_kind="headerless",
                compressed_archive_bytes=2,
                extracted_member_bytes=4,
                source_rows=1,
                arrow_ipc_bytes=1,
                parquet_bytes=3,
                parquet_footer_bytes=1,
                parquet_file_overhead_bytes=12,
                parquet_sha256="0" * 64,
                writer_identity="w",
                pyarrow_version="x",
                batches=1,
            )
            for family in PHYSICAL_FAMILIES
        ],
        objects=objects
        + [
            PhysicalObject(
                key=_key(family, "BTCUSDT", "2020-01-01"),
                family=family,
                symbol="BTCUSDT",
                economic_interval="2020-01-01",
                byte_size=10,
            )
            for family in PHYSICAL_FAMILIES
            if family != "daily/klines"
        ],
    )
    klines = next(item for item in projections if item.family == "daily/klines")
    # The largest partition is the greatest single group, never a family average.
    # The high-water partition is one logical file; multiplicity stays in the total.
    assert klines.largest_partition_bytes == ceil_div(500 * 3, 2)
    assert klines.projected_bytes == ceil_div(300 * 3, 2) * 2 + ceil_div(500 * 3, 2) * 2
    assert klines.partition_count == 2 * OUTPUT_MULTIPLICITY["daily/klines"]


def test_coinalyze_evidence_is_resolved_from_report_provenance(
    accepted: dict[str, Any]
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    evidence = resolve_coinalyze_evidence(
        authority, cache_dir=accepted["coinalyze_cache"]
    )
    assert len(evidence) == 5
    roles = {item.endpoint: item.role for item in evidence}
    # Endpoint roles are separated: one inventory, one liquidation charge witness.
    assert roles["/future-markets"] == "future_market_inventory"
    assert roles["/liquidation-history"] == "liquidation_charge_witness"
    assert roles["/open-interest-history"] == "bounded_overlap_evidence"
    for item in evidence:
        # The accepted cache is content-addressed and carries no extension.
        assert Path(item.content_path).name == item.sha256
        assert Path(item.content_path).suffix == ""


def test_coinalyze_evidence_rejects_substituted_or_escaping_bodies(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    evidence = resolve_coinalyze_evidence(
        authority, cache_dir=accepted["coinalyze_cache"]
    )
    target = Path(evidence[0].content_path)
    target.write_bytes(b"[]")
    with pytest.raises(SizingError, match="pinned identity"):
        resolve_coinalyze_evidence(authority, cache_dir=accepted["coinalyze_cache"])
    # A body outside the accepted cache is refused even when its bytes hash correctly.
    with pytest.raises(SizingError):
        resolve_coinalyze_evidence(authority, cache_dir=tmp_path / "elsewhere")


def test_supported_symbol_sets_are_compared_not_counted(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    evidence = resolve_coinalyze_evidence(
        authority, cache_dir=accepted["coinalyze_cache"]
    )
    inventory = next(item for item in evidence if item.role == "future_market_inventory")
    supported, unmapped = coinalyze_symbol_sets(authority, inventory=inventory)
    assert list(supported) == sorted(accepted["supported"])
    assert list(unmapped) == sorted(accepted["unmapped"])

    # Same counts, different symbols: a fabricated set no longer satisfies the gate.
    report = json.loads(accepted["files"]["report"].read_text())
    report["coinalyze"]["universe_support"]["supported_symbols"] = [
        f"FAKE{index}_PERP.A" for index in range(len(accepted["supported"]))
    ]
    accepted["files"]["report"].write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    monkeypatch.setattr(
        sizing, "ACCEPTED_REPORT_SHA256", _sha256(accepted["files"]["report"].read_bytes())
    )
    monkeypatch.setattr(
        sizing, "ACCEPTED_REPORT_BYTES", accepted["files"]["report"].stat().st_size
    )
    substituted = load_sizing_authority(accepted["paths"])
    with pytest.raises(SizingError, match="absent from the accepted inventory"):
        coinalyze_symbol_sets(substituted, inventory=inventory)


def test_lifecycles_come_from_accepted_evidence_and_block_when_absent(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    lifecycles, cutoff = coinalyze_lifecycles(authority, supported=accepted["supported"])
    assert cutoff == _CUTOFF
    assert set(lifecycles) == set(accepted["supported"])
    for first, last in lifecycles.values():
        assert last >= first

    metadata = json.loads(accepted["files"]["metadata"].read_text())
    metadata["symbol_snapshot"].pop("SYM0")
    accepted["files"]["metadata"].write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    monkeypatch.setattr(
        sizing,
        "ACCEPTED_CONTRACT_METADATA_SHA256",
        _sha256(accepted["files"]["metadata"].read_bytes()),
    )
    stripped = load_sizing_authority(accepted["paths"])
    # A supported mapping without authenticated bounds blocks; it never gets zero days.
    with pytest.raises(SizingError, match="no authenticated lifecycle"):
        coinalyze_lifecycles(stripped, supported=accepted["supported"])


def test_liquidation_projection_uses_its_own_parquet_envelopes(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    evidence = resolve_coinalyze_evidence(
        authority, cache_dir=accepted["coinalyze_cache"]
    )
    inventory = next(item for item in evidence if item.role == "future_market_inventory")
    supported, unmapped = coinalyze_symbol_sets(authority, inventory=inventory)
    lifecycles, _cutoff = coinalyze_lifecycles(authority, supported=supported)
    projection = project_coinalyze(
        evidence=evidence,
        supported=supported,
        unmapped=unmapped,
        lifecycles=lifecycles,
        staging=tmp_path,
    )
    # The normalized ratio is a Coinalyze envelope ratio, never a Binance family ratio.
    assert projection.envelope_numerator > 0 and projection.envelope_denominator > 0
    assert projection.envelopes
    assert projection.projected_normalized_bytes == sum(
        ceil_div(value * projection.envelope_numerator, projection.envelope_denominator)
        for value in _expected_group_bytes(projection, supported, lifecycles)
    )
    assert projection.partition_count == len(
        _expected_group_bytes(projection, supported, lifecycles)
    )
    assert projection.largest_partition_bytes > 0
    rendered = json.dumps(projection.to_dict())
    assert "apiKey" not in rendered and "api_key" not in rendered


def _expected_group_bytes(projection: Any, supported: Any, lifecycles: Any) -> list[int]:
    groups: dict[tuple[str, str], int] = {}
    for symbol in supported:
        first, last = lifecycles[symbol]
        for day in range(first, last + 1):
            month = datetime.fromordinal(day).strftime("%Y-%m")
            groups[(symbol, month)] = (
                groups.get((symbol, month), 0) + projection.point_charge_bytes
            )
    return list(groups.values())


def test_liquidation_envelope_ratio_survives_beyond_float_precision(
    tmp_path: Path
) -> None:
    measured = measure_liquidation_response(
        _liquidation_body(["BTCUSDT_PERP.A"], 3), endpoint="/liquidation-history"
    )
    symbol, tokens = measured["series"][0]
    envelope = write_liquidation_envelope(
        symbol=symbol,
        endpoint="/liquidation-history",
        tokens=tokens,
        destination=tmp_path / "liq.parquet",
    )
    assert envelope["points"] == 3
    assert envelope["parquet_bytes"] > 0
    assert envelope["parquet_footer_bytes"] > 0
    huge = 2**53
    # The same exact comparison the projection uses, past float64 resolution.
    assert ratio_exceeds((envelope["parquet_bytes"] * huge + 1, huge), (
        envelope["parquet_bytes"], 1
    ))


def test_catalog_reserve_and_publication_contracts(tmp_path: Path) -> None:
    assert operating_reserve_bytes(1) == MINIMUM_OPERATING_RESERVE_BYTES
    big = 500 * 2**30
    assert operating_reserve_bytes(big) == ceil_div(big, 5)
    with pytest.raises(SizingError):
        operating_reserve_bytes(0)
    # No caller reserve input exists at all.
    import inspect

    assert set(inspect.signature(operating_reserve_bytes).parameters) == {
        "pre_write_available_bytes"
    }
    root = tmp_path / "envelopes"
    source = tmp_path / "envelope.parquet"
    source.write_bytes(b"envelope-bytes")
    published, reused = publish_sizing_envelope(source, evidence_root=root)
    assert published.name == f"{_sha256(b'envelope-bytes')}.parquet" and reused is False
    again, reused_again = publish_sizing_envelope(source, evidence_root=root)
    assert again == published and reused_again is True
    published.write_bytes(b"tampered")
    with pytest.raises(SizingError, match="does not match its content address"):
        publish_sizing_envelope(source, evidence_root=root)
    assert not list(root.glob(".partial-*"))


def test_receipt_publication_is_idempotent_and_race_safe(tmp_path: Path) -> None:
    target = tmp_path / "180_receipt.json"
    receipt = {"schema_version": sizing.SIZING_SCHEMA_VERSION, "blockers": []}
    digest, size = publish_sizing_receipt(receipt, path=target)
    assert target.is_file() and size == target.stat().st_size
    # Republishing the identical receipt at the fixed target is idempotent.
    assert publish_sizing_receipt(receipt, path=target) == (digest, size)
    with pytest.raises(SizingError, match="already occupies"):
        publish_sizing_receipt({**receipt, "blockers": ["x"]}, path=target)
    assert not list(tmp_path.glob(".partial-*"))


def _run(accepted: dict[str, Any], tmp_path: Path, **overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "receipt_path": tmp_path / "180_receipt.json",
        "sizing_source_path": Path(sizing.__file__),
        "sizing_cli_path": Path("scripts/research/size_binance_usdm_harmonic_release.py"),
        "now": datetime(2026, 8, 22, tzinfo=UTC),
    }
    arguments.update(overrides)
    return run_storage_sizing(accepted["paths"], **arguments)


def test_end_to_end_receipt_is_complete_and_durably_identical(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    result = _run(accepted, tmp_path)
    receipt = result["receipt"]
    identity = result["receipt_file"]
    assert result["publication"]["rerun"] is False
    target = tmp_path / "180_receipt.json"
    # The returned mapping and the durable bytes are the same document.
    assert target.read_bytes() == sizing.canonical_json(receipt)
    assert identity["receipt_sha256"] == _sha256(target.read_bytes())
    assert "receipt_sha256" not in receipt
    for section in (
        "authority",
        "physical_inputs",
        "cohort",
        "measurements",
        "projections",
        "coinalyze",
        "counts",
        "partitioning",
        "filesystem",
        "capacity",
        "blockers",
        "code_identity",
    ):
        assert section in receipt
    assert receipt["storage_preflight_state"] in {STATE_SUFFICIENT, STATE_BLOCKED}
    assert receipt["code_identity"]["sizing_source_sha256"]
    assert receipt["physical_inputs"]["combined_objects"] == sizing.ACCEPTED_COMBINED_OBJECTS
    assert (
        receipt["physical_inputs"]["projected_new_binance_raw_bytes"]
        == sizing.ACCEPTED_NEW_BINANCE_RAW_BYTES
    )
    capacity = receipt["capacity"]
    assert capacity["total_future_storage_bytes"] == (
        capacity["new_binance_raw_bytes"]
        + capacity["new_coinalyze_raw_bytes"]
        + capacity["normalized_catalog_bytes"]
        + capacity["temporary_high_water_bytes"]
        + capacity["operating_reserve_bytes"]
    )
    assert capacity["operating_reserve_bytes"] >= MINIMUM_OPERATING_RESERVE_BYTES
    filesystem = receipt["filesystem"]
    assert filesystem["durable_receipt_bytes"] > 0
    assert filesystem["retained_sizing_evidence_bytes"] > 0
    counts = receipt["counts"]
    assert counts["count_sources"]["typed_gap_rows"].startswith("report coinalyze")
    assert receipt["partitioning"]["catalog_overhead_bytes"] == (
        (
            counts["physical_raw_objects"]
            + counts["projected_normalized_files"]
            + counts["typed_gap_rows"]
            + counts["membership_rows"]
            + counts["coinalyze_receipts"]
        )
        * CATALOG_PAGE_BYTES
        + sizing.ACCEPTED_REPORT_BYTES
        + sizing.ACCEPTED_MANIFEST_DETAIL_BYTES
    )


def test_rerun_returns_the_identical_receipt_under_changed_observations(
    accepted: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _run(accepted, tmp_path)
    target = tmp_path / "180_receipt.json"
    published = target.read_bytes()
    assert first["publication"]["envelopes_published"] > 0
    assert first["publication"]["envelopes_reused"] == 0

    # Second invocation: every envelope is now reused, free space has moved far enough to
    # change a one-fifth reserve, and the measurement instant is different. None of that
    # may change the durable receipt.
    observed = first["receipt"]["filesystem"]["pre_write_available_bytes"]
    moved = observed + 200 * 2**30
    assert operating_reserve_bytes(moved) != operating_reserve_bytes(observed)
    monkeypatch.setattr(sizing, "measure_available_bytes", lambda path: moved)
    second = _run(accepted, tmp_path, now=datetime(2026, 8, 23, tzinfo=UTC))
    assert second["publication"]["rerun"] is True
    assert second["publication"]["envelopes_reused"] > 0
    assert second["publication"]["envelopes_published"] == 0
    assert target.read_bytes() == published
    assert second["receipt"] == first["receipt"]
    assert second["receipt_file"] == first["receipt_file"]


def test_rerun_below_the_reserve_floor_also_returns_the_identical_receipt(
    accepted: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _run(accepted, tmp_path)
    published = (tmp_path / "180_receipt.json").read_bytes()
    # Above the 80 GiB threshold the reserve is one fifth of availability, so a changed
    # observation changes the derived reserve. The frozen receipt still stands.
    high = 400 * 2**30
    assert operating_reserve_bytes(high) > MINIMUM_OPERATING_RESERVE_BYTES
    monkeypatch.setattr(sizing, "measure_available_bytes", lambda path: high)
    second = _run(accepted, tmp_path)
    assert second["publication"]["rerun"] is True
    assert (tmp_path / "180_receipt.json").read_bytes() == published
    assert second["receipt"] == first["receipt"]


@pytest.mark.parametrize(
    "section",
    [
        "cohort",
        "measurements",
        "filesystem",
        "blockers",
        "storage_preflight_state",
        "authorization",
        "capacity",
    ],
)
def test_a_tampered_prior_receipt_is_never_reused(
    accepted: dict[str, Any], tmp_path: Path, section: str
) -> None:
    first = _run(accepted, tmp_path)
    target = tmp_path / "180_receipt.json"
    document = json.loads(target.read_text())
    if section == "cohort":
        document["cohort"]["unique_samples"] = int(document["cohort"]["unique_samples"]) + 1
    elif section == "measurements":
        document["measurements"] = document["measurements"][:-1]
    elif section == "filesystem":
        document["filesystem"]["durable_receipt_bytes"] = 1
    elif section == "blockers":
        document["blockers"] = ["fabricated_reason"]
    elif section == "storage_preflight_state":
        document["storage_preflight_state"] = "sufficient"
        document["blockers"] = ["component_unknown_or_non_integer"]
    elif section == "authorization":
        document["authorization"] = "gate 2 accepted"
    else:
        document["capacity"]["total_future_storage_bytes"] = 1
    # Canonically reserialized, so canonical form alone cannot vouch for it.
    target.write_bytes(sizing.canonical_json(document))
    assert first["receipt"] != document
    with pytest.raises(SizingError, match="already occupies"):
        _run(accepted, tmp_path)
    # The forged prior is never adopted and never overwritten.
    assert target.read_bytes() == sizing.canonical_json(document)


def test_a_foreign_receipt_at_the_fixed_target_is_never_overwritten(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    target = tmp_path / "180_receipt.json"
    target.write_text(json.dumps({"schema_version": "other"}, indent=2, sort_keys=True) + "\n")
    before = target.read_bytes()
    with pytest.raises(SizingError, match="already occupies"):
        _run(accepted, tmp_path)
    assert target.read_bytes() == before


def test_capacity_shortfall_blocks_without_false_acceptance(
    accepted: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sizing, "measure_available_bytes", lambda path: 4_096)
    result = _run(accepted, tmp_path)
    receipt = result["receipt"]
    assert receipt["storage_preflight_state"] == STATE_BLOCKED
    assert sizing.BLOCKER_CAPACITY in receipt["blockers"]
    assert "authorizes no acquisition" in receipt["authorization"]


def test_sizing_touches_only_its_own_evidence(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    store = accepted["store"]
    before = {
        str(path.relative_to(store)): _sha256(path.read_bytes())
        for path in sorted(store.rglob("*"))
        if path.is_file()
    }
    _run(accepted, tmp_path)
    after = {
        str(path.relative_to(store)): _sha256(path.read_bytes())
        for path in sorted(store.rglob("*"))
        if path.is_file()
    }
    changed = {name for name in set(before) | set(after) if before.get(name) != after.get(name)}
    assert changed
    assert all(name.startswith(sizing.SIZING_EVIDENCE_ROOT) for name in changed)
    for name, digest in before.items():
        assert after[name] == digest


def test_no_network_no_credential_and_no_caller_policy() -> None:
    source = Path(sizing.__file__).read_text(encoding="utf-8")
    cli = Path("scripts/research/size_binance_usdm_harmonic_release.py").read_text(
        encoding="utf-8"
    )
    # Guard the actual network surface, not harmless receipt field names.
    for forbidden in (
        "import httpx",
        "import requests",
        "import socket",
        "urllib.request",
        "COINALYZE_API_KEY",
        "api_key=",
    ):
        assert forbidden not in source
        assert forbidden not in cli
    # The receipt legitimately describes request framing; that must stay allowed.
    assert "request_framing" in source


def test_cli_accepts_only_accepted_byte_locations() -> None:
    import ast

    source = Path("scripts/research/size_binance_usdm_harmonic_release.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    options = [
        str(node.args[0].value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]
    assert options
    forbidden = (
        "cohort",
        "family",
        "coefficient",
        "multiplicity",
        "compression",
        "batch",
        "overhead",
        "credit",
        "reserve",
        "capacity",
        "ratio",
        "lifecycle",
        "coinalyze",
        "receipt",
        "cutoff",
    )
    for option in options:
        assert not any(word in option for word in forbidden), option
        assert option.endswith(("-path", "-root"))
    # The receipt destination is the fixed reviewed target, not an operator choice.
    assert "SIZING_RECEIPT_RELATIVE_PATH" in source
    assert "receipt_path=repository / SIZING_RECEIPT_RELATIVE_PATH" in source
    assert "return 0" in source


def test_receipt_accounts_for_its_own_exact_length(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    result = _run(accepted, tmp_path)
    receipt = result["receipt"]
    target = tmp_path / "180_receipt.json"
    exact = target.stat().st_size
    # The receipt's declared length is the published document's own length.
    assert receipt["filesystem"]["durable_receipt_bytes"] == exact
    assert result["receipt_file"]["receipt_bytes"] == exact
    assert len(sizing.canonical_json(receipt)) == exact
    # Sufficiency compares with the space left after evidence and this exact receipt.
    assert receipt["filesystem"]["post_publication_available_bytes"] == (
        result["publication"]["available_bytes_after_evidence"] - exact
    )


def test_coinalyze_equation_uses_exact_retained_response_identity(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    receipt = _run(accepted, tmp_path)["receipt"]
    block = receipt["coinalyze"]
    inventory_bytes = next(
        int(item["byte_size"])
        for item in block["evidence"]
        if item["role"] == "future_market_inventory"
    )
    liquidation_bytes = next(
        int(item["byte_size"])
        for item in block["evidence"]
        if item["role"] == "liquidation_charge_witness"
    )
    # Gross includes the exact inventory receipt plus the one-symbol liquidation
    # projection; retained credit is the two retained responses' own exact byte sizes.
    assert block["gross_inventory_bytes"] == inventory_bytes
    assert block["gross_required_raw_bytes"] == (
        block["gross_inventory_bytes"] + block["gross_liquidation_bytes"]
    )
    assert block["retained_inventory_receipts"] == 1
    assert block["retained_inventory_bytes"] == inventory_bytes
    assert block["retained_liquidation_receipts"] == 1
    assert block["retained_liquidation_bytes"] == liquidation_bytes
    # One retained request, two covered symbols: the receipt count is not the symbol count.
    assert block["retained_receipts"] == 2
    assert block["retained_covered_symbols"] == 2
    assert block["retained_receipts"] != block["retained_covered_symbols"] + 1
    assert block["retained_raw_bytes"] == inventory_bytes + liquidation_bytes
    assert block["gross_required_raw_bytes"] - block["retained_raw_bytes"] == (
        block["projected_new_raw_bytes"]
    )
    assert receipt["capacity"]["new_coinalyze_raw_bytes"] == block["projected_new_raw_bytes"]
    # Only proved unique in-lifecycle daily points are credited.
    assert block["retained_points"] == 10
    # Projected acquisition receipts are one per supported mapping plus one inventory.
    assert block["liquidation_receipts"] == len(accepted["supported"])
    assert block["inventory_receipts"] == 1
    assert block["projected_acquisition_receipts"] == len(accepted["supported"]) + 1
    assert block["overlap_evidence_receipts"] == 3
    counts = receipt["counts"]
    assert counts["projected_coinalyze_receipts"] == block["projected_acquisition_receipts"]
    assert counts["retained_coinalyze_evidence_records"] == 5
    assert receipt["partitioning"]["catalog_overhead_bytes"] == (
        counts["catalog_pages"] * CATALOG_PAGE_BYTES
        + sizing.ACCEPTED_REPORT_BYTES
        + sizing.ACCEPTED_MANIFEST_DETAIL_BYTES
    )


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        ("unsupported_symbol", "unsupported symbol"),
        ("outside_lifecycle", "outside its authenticated lifecycle"),
        ("not_daily", "pinned identity"),
    ],
)
def test_retained_liquidation_coverage_is_validated_before_credit(
    accepted: dict[str, Any], tamper: str, message: str
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    evidence = resolve_coinalyze_evidence(
        authority, cache_dir=accepted["coinalyze_cache"]
    )
    inventory = next(item for item in evidence if item.role == "future_market_inventory")
    supported, _unmapped = coinalyze_symbol_sets(authority, inventory=inventory)
    lifecycles, _cutoff = coinalyze_lifecycles(authority, supported=supported)
    if tamper == "unsupported_symbol":
        body = _liquidation_body(["NOTLISTED_PERP.A"], 3)
    elif tamper == "outside_lifecycle":
        body = json.dumps(
            [
                {
                    "symbol": "SYM0_PERP.A",
                    "history": [{"t": 1_000_000, "l": "1", "s": "2"}],
                }
            ]
        ).encode("utf-8")
    else:
        body = json.dumps(
            [
                {
                    "symbol": "SYM0_PERP.A",
                    "history": [
                        {"t": 1577836800, "l": "1", "s": "2"},
                        {"t": 1577836800 + 2 * 86_400, "l": "1", "s": "2"},
                    ],
                }
            ]
        ).encode("utf-8")
    measured = measure_liquidation_response(body, endpoint="/liquidation-history")
    with pytest.raises(SizingError, match=message):
        sizing.validate_retained_liquidation_coverage(
            measured,
            supported=supported,
            lifecycles=lifecycles,
            endpoint="/liquidation-history",
        )


def test_repeated_retained_days_are_credited_once(accepted: dict[str, Any]) -> None:
    authority = load_sizing_authority(accepted["paths"])
    evidence = resolve_coinalyze_evidence(
        authority, cache_dir=accepted["coinalyze_cache"]
    )
    inventory = next(item for item in evidence if item.role == "future_market_inventory")
    supported, _unmapped = coinalyze_symbol_sets(authority, inventory=inventory)
    lifecycles, _cutoff = coinalyze_lifecycles(authority, supported=supported)
    measured = measure_liquidation_response(
        _liquidation_body(["SYM0_PERP.A"], 4), endpoint="/liquidation-history"
    )
    covered = sizing.validate_retained_liquidation_coverage(
        measured,
        supported=supported,
        lifecycles=lifecycles,
        endpoint="/liquidation-history",
    )
    assert covered["symbols"] == ["SYM0_PERP.A"]
    assert covered["unique_in_lifecycle_points"] == 4
    assert covered["points_per_symbol"] == {"SYM0_PERP.A": 4}


def test_largest_partition_is_one_logical_file(tmp_path: Path) -> None:
    def _measurement(family: str) -> Any:
        return sizing.EnvelopeMeasurement(
            key=f"k-{family}",
            family=family,
            symbol="BTCUSDT",
            economic_interval="2020-01-01",
            schema_kind="headerless",
            compressed_archive_bytes=2,
            extracted_member_bytes=4,
            source_rows=1,
            arrow_ipc_bytes=1,
            parquet_bytes=3,
            parquet_footer_bytes=1,
            parquet_file_overhead_bytes=12,
            parquet_sha256="0" * 64,
            writer_identity="w",
            pyarrow_version="x",
            batches=1,
        )

    objects = [
        PhysicalObject(
            key=_key(family, "BTCUSDT", "2020-01-01"),
            family=family,
            symbol="BTCUSDT",
            economic_interval="2020-01-01",
            byte_size=500,
        )
        for family in PHYSICAL_FAMILIES
    ]
    projections = project_families(
        measurements=[_measurement(family) for family in PHYSICAL_FAMILIES],
        objects=objects,
    )
    single = ceil_div(500 * 3, 2)
    fan_out = next(item for item in projections if item.family == "daily/klines")
    plain = next(item for item in projections if item.family == "daily/bookDepth")
    # Multiplicity two means two logical files, not one file of twice the size.
    assert OUTPUT_MULTIPLICITY["daily/klines"] == 2
    assert fan_out.largest_partition_bytes == single
    assert fan_out.projected_bytes == single * 2
    assert fan_out.partition_count == 2
    # Multiplicity one is the same single file.
    assert plain.largest_partition_bytes == single
    assert plain.projected_bytes == single
    assert plain.partition_count == 1


def test_lifecycle_conversion_is_integer_only() -> None:
    source = Path(sizing.__file__).read_text(encoding="utf-8")
    assert "// 1000" in source
    assert "/ 1000" not in source.replace("// 1000", "")
    day = sizing._utc_day_from_ms(_ONBOARD_MS + 999)
    assert day == sizing._utc_day_from_ms(_ONBOARD_MS)
    assert isinstance(day, int)


def test_publication_streams_and_refuses_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "envelopes"
    root.mkdir()
    source = tmp_path / "envelope.parquet"
    source.write_bytes(b"x" * (2 * 1024 * 1024 + 7))
    published, reused = publish_sizing_envelope(source, evidence_root=root)
    # A multi-megabyte file is copied through bounded reads and lands intact.
    assert published.stat().st_size == source.stat().st_size
    assert reused is False
    assert not list(root.glob(".partial-*"))

    # A symlinked evidence root is refused rather than followed.
    linked_root = tmp_path / "linked"
    linked_root.symlink_to(root, target_is_directory=True)
    with pytest.raises(SizingError, match="symbolic link|not a real directory"):
        publish_sizing_envelope(source, evidence_root=linked_root)

    receipt_dir = tmp_path / "receipts"
    receipt_dir.mkdir()
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text("{}\n")
    linked_receipt = receipt_dir / "180.json"
    linked_receipt.symlink_to(elsewhere)
    with pytest.raises(SizingError, match="symbolic link|already occupies|not a regular"):
        publish_sizing_receipt({"schema_version": "x"}, path=linked_receipt)
    # The symlink target is untouched.
    assert elsewhere.read_text() == "{}\n"


def test_publication_cleans_up_and_survives_a_racing_target(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    receipt = {"schema_version": sizing.SIZING_SCHEMA_VERSION}
    # A racing identical publication is accepted; a racing different one is refused.
    target.write_bytes(sizing.canonical_json(receipt))
    digest, size = publish_sizing_receipt(receipt, path=target)
    assert size == target.stat().st_size and digest
    target.write_bytes(b'{"schema_version": "other"}\n')
    with pytest.raises(SizingError, match="already occupies"):
        publish_sizing_receipt(receipt, path=target)
    assert not list(tmp_path.glob(".partial-*"))


def test_publication_refuses_a_symlink_swapped_after_the_check(tmp_path: Path) -> None:
    root = tmp_path / "envelopes"
    root.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    source = tmp_path / "envelope.parquet"
    source.write_bytes(b"envelope-bytes")
    digest = _sha256(b"envelope-bytes")
    # A symlink already standing at the content address is refused, not followed.
    victim = elsewhere / "victim"
    victim.write_bytes(b"original")
    (root / f"{digest}.parquet").symlink_to(victim)
    with pytest.raises(SizingError, match="not a regular file"):
        publish_sizing_envelope(source, evidence_root=root)
    # The symlink target is untouched.
    assert victim.read_bytes() == b"original"


def test_prior_receipt_reads_never_follow_a_symlink(tmp_path: Path) -> None:
    target = tmp_path / "180_receipt.json"
    elsewhere = tmp_path / "secret.json"
    elsewhere.write_bytes(sizing.canonical_json({"schema_version": "other"}))
    target.symlink_to(elsewhere)
    with pytest.raises(SizingError, match="not a regular file"):
        sizing.revalidate_prior_receipt(target, expected={})
    assert elsewhere.read_bytes() == sizing.canonical_json({"schema_version": "other"})


def test_publication_uses_validated_directory_descriptors(tmp_path: Path) -> None:
    import inspect

    source = inspect.getsource(sizing._publish_at)
    # Staging, linking, comparison, fsync, and cleanup all run through the descriptor.
    assert "dir_fd=directory" in source
    assert "src_dir_fd=directory" in source and "dst_dir_fd=directory" in source
    assert "os.fsync(directory)" in source
    assert "os.unlink(tmp_name, dir_fd=directory)" in source
    assert "O_NOFOLLOW" in source
    envelope = inspect.getsource(sizing.publish_sizing_envelope)
    # The existing target is hashed through the descriptor, not by pathname.
    assert "_hash_at_no_follow(directory, name)" in envelope
    assert "compute_sha256(dest)" not in envelope
    directory = inspect.getsource(sizing._open_directory_no_follow)
    assert "O_DIRECTORY" in directory and "O_NOFOLLOW" in directory


def test_racing_targets_are_accepted_only_when_identical(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    receipt = {"schema_version": sizing.SIZING_SCHEMA_VERSION}
    body = sizing.canonical_json(receipt)
    # An identical racing target is adopted; a different one is refused.
    target.write_bytes(body)
    digest, size = publish_sizing_receipt(receipt, path=target)
    assert (digest, size) == (_sha256(body), len(body))
    target.write_bytes(sizing.canonical_json({"schema_version": "other"}))
    with pytest.raises(SizingError, match="already occupies"):
        publish_sizing_receipt(receipt, path=target)
    # Every branch cleans up its temporary file.
    assert not list(tmp_path.glob(".partial-*"))
    root = tmp_path / "envelopes"
    root.mkdir()
    source = tmp_path / "envelope.parquet"
    source.write_bytes(b"payload")
    publish_sizing_envelope(source, evidence_root=root)
    assert not list(root.glob(".partial-*"))
