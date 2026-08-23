"""CEX-002 ADR-0021 — prove the bounded real-sample storage sizing contract.

The fixtures reproduce the accepted evidence *shapes*: a ten-family manifest detail, a
separate two-family cost manifest resolved through retained listing responses, and
report-bound Coinalyze provenance in a content-addressed cache whose files carry no
extension. Manifest consumability and Gate-2 retained credit are shaped as the two
separate ADR-0023 authorities they are. The pinned production identities and totals
cannot be reproduced at fixture scale, so they are re-pointed per fixture; one test
asserts the literal accepted values on their own.
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
    verify_retained_object,
)
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    ARCHIVE_FAMILIES,
    CATALOG_PAGE_BYTES,
    COST_FAMILIES,
    MINIMUM_OPERATING_RESERVE_BYTES,
    OUTPUT_MULTIPLICITY,
    PHYSICAL_FAMILIES,
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


def _find(
    rows: list[dict[str, Any]], family: str, symbol: str, interval: str
) -> dict[str, Any]:
    return next(
        row
        for row in rows
        if row["family"] == family
        and row["symbol"] == symbol
        and row["economic_interval"] == interval
    )


def _base(row: dict[str, Any]) -> str:
    return str(row["key"]).rsplit("/", 1)[-1]


def _market_row(provider: str, native: str) -> dict[str, Any]:
    """One complete future-market row, binding a provider identity to its native one."""
    return {
        "symbol": provider,
        "symbol_on_exchange": native,
        "exchange": "A",
        "is_perpetual": True,
        "base_asset": native[:-4] if native.endswith("USDT") else native,
        "quote_asset": "USDT",
        "oi_lq_vol_denominated_in": "USD",
    }


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
                        # Only a few manifest rows carry the consumable publication
                        # flag. ADR-0023 keeps that fact separate from Gate-2 credit,
                        # which is re-proved over the whole requirement. Both Kline
                        # families are included so basenames genuinely collide.
                        "consumable": (
                            family in ("daily/klines", "monthly/klines")
                            and interval != "2020-02-01"
                        ),
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
                        # Cost keys never carry the manifest flag; ADR-0023 credits
                        # them through the complete-cost side of the requirement.
                        "consumable": False,
                    }
                )

    detail_path = store / "manifest_detail.jsonl.gz"
    with gzip.GzipFile(detail_path, mode="wb", compresslevel=9, mtime=0) as handle:
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
    cohort_rows = [
        next(
            row
            for row in (selected_rows + cost_rows)
            if row["family"] == family and not row.get("consumable")
        )
        for family in PHYSICAL_FAMILIES
    ]
    consumable_rows = [row for row in selected_rows if row["consumable"]]
    # ADR-0023: manifest consumability is a separate fact. The Gate-2 credit domain is
    # every effective checkpoint row inside the selected-plus-cost requirement, so the
    # non-consumable cohort rows below are credited too.
    seeded_rows = consumable_rows + cost_rows
    assert consumable_rows and len(seeded_rows) != len(cohort_rows)
    # One consumable Kline row is a persisted basename-only recovery. Its stem is also
    # the stem of the other Kline family's exact key, so the complete frozen candidate
    # domain resolves it two ways and it is credited nothing however well it rehashes.
    ambiguous_row = _find(consumable_rows, "daily/klines", "BTCUSDT", "2020-01-01")
    # Its exact-key twin: identical basename, never recovered, therefore fully valid.
    collision_twin = _find(consumable_rows, "monthly/klines", "BTCUSDT", "2020-01-01")
    # A basename-unique recovery. The domain binds it, so recovery costs it nothing.
    unique_recovered = _find(cost_rows, "daily/bookTicker", "BTCUSDT", "2020-01-01")
    # Two distinct valid keys over one retained object: two logical keys, one object.
    duplicate_source = _find(consumable_rows, "daily/klines", "ETHUSDT", "2020-01-02")
    duplicate_row = _find(consumable_rows, "monthly/klines", "ETHUSDT", "2020-01-02")
    domain_stems = [_base(row) for row in selected_rows + cost_rows]
    assert _base(ambiguous_row) == _base(collision_twin)
    assert domain_stems.count(_base(ambiguous_row)) == 2
    assert _base(duplicate_source) == _base(duplicate_row)
    assert domain_stems.count(_base(unique_recovered)) == 1

    unique_rows: list[dict[str, Any]] = []
    for row in cohort_rows + seeded_rows:
        if all(str(row["key"]) != str(item["key"]) for item in unique_rows):
            unique_rows.append(row)
    # A distinct row count per row keeps every other retained object distinct, so the
    # only duplicate content in the store is the one this fixture declares.
    payloads = {
        str(row["key"]): _zip("data.csv", _csv(str(row["family"]), 3 + index))
        for index, row in enumerate(unique_rows)
    }
    payloads[str(duplicate_row["key"])] = payloads[str(duplicate_source["key"])]
    recovered_keys = {str(ambiguous_row["key"]), str(unique_recovered["key"])}
    for row in unique_rows:
        key = str(row["key"])
        family = str(row["family"])
        payload = payloads[key]
        digest = _sha256(payload)
        (raw / digest).write_bytes(payload)
        sidecar_body = f"{digest}  {key.rsplit('/', 1)[-1]}\n".encode()
        sidecar_path, sidecar_digest = persist_provider_sidecar(
            sidecar_body, sidecar_dir=listing_cache
        )
        entry: dict[str, Any] = {
            "status": "complete",
            "sha256": digest,
            "byte_size": len(payload),
            "url": f"https://data.binance.vision/{key}",
            "provider_checksum": digest,
            "checksum_match": True,
            "schema_kind": "headerless",
            "schema_fields": list(KNOWN_ARCHIVE_SCHEMAS[_hint(family)]["headerless"]),
            "provider_checksum_path": str(sidecar_path),
            "provider_checksum_sha256": sidecar_digest,
        }
        if key in recovered_keys:
            entry["recovered_from_retained_bytes"] = True
        checkpoint_objects[key] = entry
    for index, row in enumerate(cohort_rows):
        plan_entries.append(
            {
                "family": str(row["family"]),
                "symbol": row["symbol"],
                "key": row["key"],
                "url": f"https://data.binance.vision/{row['key']}",
                "action": "download" if index % 2 else "reuse_retained",
                "byte_size": len(payloads[str(row["key"])]),
            }
        )
    rejected_keys = [str(ambiguous_row["key"])]
    # Every effective checkpoint row in the requirement earns credit unless it is
    # rejected lineage. This deliberately includes the non-consumable cohort rows, so a
    # valid selected key with no manifest consumable flag still earns selected credit.
    credited_rows = [
        row for row in unique_rows if str(row["key"]) not in set(rejected_keys)
    ]
    unconsumable_credited = [
        row
        for row in credited_rows
        if row["family"] in ARCHIVE_FAMILIES and not row["consumable"]
    ]
    assert unconsumable_credited
    credited_objects: dict[str, int] = {}
    for row in credited_rows:
        payload = payloads[str(row["key"])]
        credited_objects.setdefault(_sha256(payload), len(payload))
    aliases = [dict(plan_entries[0], action="alias"), dict(plan_entries[1], action="alias")]
    plan_entries.extend(aliases)

    # The real namespaces, mirrored exactly: Binance-native identities carry the
    # supported set, membership, and lifecycles, while the retained Coinalyze API
    # bodies carry provider identities. The inventory is the only thing that binds them.
    supported_natives = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
    # Binance perpetuals the inventory also validates but this projection never counts.
    extra_natives = ("DOGEUSDT", "ADAUSDT")
    provider_of = {native: f"{native}_PERP.A" for native in supported_natives + extra_natives}
    anchor_natives = ("BTCUSDT", "ETHUSDT")
    inventory_rows = [
        _market_row(provider_of[native], native)
        for native in supported_natives + extra_natives
    ]
    # Real inventory noise: another venue, and a Binance non-perpetual. Neither may
    # enter the Binance perpetual identity map or the supported projection.
    inventory_rows.append(dict(_market_row("BTCUSD_PERP.F", "BTCUSD"), exchange="F"))
    inventory_rows.append(
        dict(_market_row("BTCUSDT_240628.A", "BTCUSDT_240628"), is_perpetual=False)
    )
    inventory_body = json.dumps(inventory_rows).encode("utf-8")
    # The accepted shape: one retained request whose single response carries two symbols,
    # each named by its Coinalyze provider identity.
    liquidation_body = _liquidation_body(
        [provider_of[native] for native in anchor_natives], 5
    )
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
        # The exact accepted ten-field shape. `header_names` records only the name of
        # the request header the key travelled in; no header value is ever published.
        provenance.append(
            {
                "byte_size": len(body),
                "content_path": str(coinalyze_cache / digest),
                "header_names": ["api_key"],
                "params": {
                    "symbols": ",".join(provider_of[n] for n in anchor_natives),
                    "interval": "daily",
                    "from": "1577836800",
                    "to": "1585612800",
                },
                "path": endpoint,
                "provenance_source": "raw_response_bytes",
                "retrieved_at": "2026-08-21T00:00:00+00:00",
                "sha256": digest,
                "status_code": 200,
                "transport": "network",
            }
        )

    supported = list(supported_natives)
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
        # Official contract metadata is keyed by Binance-native identity.
        "symbol_snapshot": {
            native: {"onboard_ms": _ONBOARD_MS, "close_ms": None}
            for native in supported_natives
        },
    }
    report = {
        "generated_at": _CUTOFF,
        "plan_lock": {"plan_version": 4, "plan_digest": "9" * 64, "inputs": inputs},
        # ADR-0022 names the rejected legacy rows in two places, and they agree.
        "resume": {
            "rejected_ambiguous_retained_keys": list(rejected_keys),
            "rejected_ambiguous_retained_count": len(rejected_keys),
        },
        "storage": {
            "cost_sample": {"keys": [row["key"] for row in cost_rows]},
            "gate2_feasibility": {
                "rejected_retained_rows": [
                    {"key": key, "reason": "ambiguous_recovered_basename"}
                    for key in rejected_keys
                ],
                "rejected_retained_row_count": len(rejected_keys),
                # The report states the retained quantities it accepted, so the sizing
                # consumer proves them by name and not only through the report digest.
                "retained_valid_requirement_keys": len(credited_rows),
                "retained_verified_credit_objects": len(credited_objects),
                "retained_verified_credit_bytes": sum(credited_objects.values()),
                "unverified_retained_objects": 0,
            },
        },
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
            # Header authentication only: the key never enters a query string.
            "key_present": True,
            "key_location": "header",
            "query_contains_key": False,
            # The inventory validates every Binance perpetual, not only the supported
            # projection, and the report declares that count both ways.
            "binance_perpetual_market_count": len(supported_natives) + len(extra_natives),
            "native_identity_validated_markets": (
                len(supported_natives) + len(extra_natives)
            ),
            "native_identity_source": "future-markets.symbol_on_exchange",
            "anchor_symbols": list(anchor_natives),
            "anchor_identity": [
                {
                    "native_symbol": native,
                    "symbol_on_exchange": native,
                    "provider_symbol": provider_of[native],
                }
                for native in anchor_natives
            ],
            "requested_symbols": [provider_of[native] for native in anchor_natives],
            "matched_markets": sorted(provider_of[native] for native in anchor_natives),
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
        # The separate ADR-0023 manifest publication fact, never a credit quantity.
        "ACCEPTED_MANIFEST_CONSUMABLE_ROWS": len(consumable_rows),
        # Three separate ADR-0022 quantities: valid logical keys, unique objects, bytes,
        # split by ADR-0023 membership in the selected and cost requirement sets.
        "ACCEPTED_RETAINED_CREDIT_KEYS": len(credited_rows),
        "ACCEPTED_SELECTED_RETAINED_KEYS": len(
            [row for row in credited_rows if row["family"] in ARCHIVE_FAMILIES]
        ),
        "ACCEPTED_COST_RETAINED_KEYS": len(
            [row for row in credited_rows if row["family"] in COST_FAMILIES]
        ),
        "ACCEPTED_REJECTED_RECOVERED_ROWS": len(rejected_keys),
        "ACCEPTED_UNVERIFIED_RETAINED_OBJECTS": 0,
        "ACCEPTED_RETAINED_CREDIT_OBJECTS": len(credited_objects),
        "ACCEPTED_RETAINED_CREDIT_BYTES": sum(credited_objects.values()),
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
    # Every pinned artifact is addressable by name, including the three that are not
    # written by the document loop above.
    paths["detail"] = detail_path
    paths["source"] = source_path
    paths["cli"] = cli_path
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
        "supported_natives": list(supported_natives),
        "extra_natives": list(extra_natives),
        "anchor_natives": list(anchor_natives),
        "provider_of": dict(provider_of),
        "inventory_rows": inventory_rows,
        "unmapped": unmapped,
        "cohort_rows": cohort_rows,
        "seeded_rows": seeded_rows,
        "credited_rows": credited_rows,
        "consumable_rows": consumable_rows,
        "unconsumable_credited": unconsumable_credited,
        "credited_objects": credited_objects,
        "rejected_keys": rejected_keys,
        "ambiguous_row": ambiguous_row,
        "collision_twin": collision_twin,
        "unique_recovered": unique_recovered,
        "duplicate_source": duplicate_source,
        "duplicate_row": duplicate_row,
        "payloads": payloads,
        "pins": pins,
    }


def test_pinned_record218_identities_are_literal() -> None:
    """Every authority identity is the record-218 one, written out in full."""
    assert sizing.ACCEPTED_REPORT_SHA256 == (
        "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
    )
    assert sizing.ACCEPTED_REPORT_BYTES == 13_745_360
    assert sizing.ACCEPTED_MANIFEST_DETAIL_SHA256 == (
        "64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113"
    )
    assert sizing.ACCEPTED_MANIFEST_DETAIL_BYTES == 11_292_635
    assert sizing.ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_SHA256 == (
        "d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17"
    )
    assert sizing.ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_BYTES == 466_714_158
    assert sizing.ACCEPTED_LOCK_SHA256 == (
        "6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e"
    )
    assert sizing.ACCEPTED_AMENDMENT_LEDGER_SHA256 == (
        "2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf"
    )
    assert sizing.ACCEPTED_QUALIFICATION_SOURCE_SHA256 == (
        "2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74"
    )
    assert sizing.ACCEPTED_QUALIFICATION_CLI_SHA256 == (
        "473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f"
    )
    assert sizing.ACCEPTED_PROGRESS_CHECKPOINT_SHA256 == (
        "cc8e02389d182e6d76d00b913503d95f72a352d883c50ffd81dd3c49df157b2f"
    )
    assert sizing.ACCEPTED_LISTING_CHECKPOINT_SHA256 == (
        "d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a"
    )
    assert sizing.ACCEPTED_CONTRACT_METADATA_SHA256 == (
        "7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42"
    )
    # No identity above may be a placeholder or a repeat of another artifact.
    identities = (
        sizing.ACCEPTED_REPORT_SHA256,
        sizing.ACCEPTED_MANIFEST_DETAIL_SHA256,
        sizing.ACCEPTED_MANIFEST_DETAIL_UNCOMPRESSED_SHA256,
        sizing.ACCEPTED_LOCK_SHA256,
        sizing.ACCEPTED_AMENDMENT_LEDGER_SHA256,
        sizing.ACCEPTED_QUALIFICATION_SOURCE_SHA256,
        sizing.ACCEPTED_QUALIFICATION_CLI_SHA256,
        sizing.ACCEPTED_PROGRESS_CHECKPOINT_SHA256,
        sizing.ACCEPTED_LISTING_CHECKPOINT_SHA256,
        sizing.ACCEPTED_CONTRACT_METADATA_SHA256,
    )
    assert len(set(identities)) == len(identities)
    assert all(len(item) == 64 and set(item) <= set("0123456789abcdef") for item in identities)
    # The exact accepted physical requirement, and its two separate authorities.
    assert sizing.ACCEPTED_SELECTED_OBJECTS == 733_203
    assert sizing.ACCEPTED_SELECTED_BYTES == 7_833_966_625
    assert sizing.ACCEPTED_COST_OBJECTS == 3_144
    assert sizing.ACCEPTED_COST_BYTES == 12_522_974_218
    assert sizing.ACCEPTED_COMBINED_OBJECTS == 736_347
    assert sizing.ACCEPTED_COMBINED_BYTES == 20_356_940_843
    assert sizing.ACCEPTED_RETAINED_CREDIT_OBJECTS == 73
    assert sizing.ACCEPTED_RETAINED_CREDIT_BYTES == 5_225_416
    # ADR-0022's three distinct quantities, split by ADR-0023's proved membership.
    assert sizing.ACCEPTED_RETAINED_CREDIT_KEYS == 73
    assert sizing.ACCEPTED_SELECTED_RETAINED_KEYS == 68
    assert sizing.ACCEPTED_COST_RETAINED_KEYS == 5
    assert (
        sizing.ACCEPTED_SELECTED_RETAINED_KEYS + sizing.ACCEPTED_COST_RETAINED_KEYS
        == sizing.ACCEPTED_RETAINED_CREDIT_KEYS
    )
    # The manifest's separate publication fact. It is neither side of the credit split,
    # and no credit quantity may be inferred by subtracting it from the credit total.
    assert sizing.ACCEPTED_MANIFEST_CONSUMABLE_ROWS == 56
    assert sizing.ACCEPTED_MANIFEST_CONSUMABLE_ROWS != (
        sizing.ACCEPTED_SELECTED_RETAINED_KEYS
    )
    assert (
        sizing.ACCEPTED_RETAINED_CREDIT_KEYS - sizing.ACCEPTED_MANIFEST_CONSUMABLE_ROWS
        != sizing.ACCEPTED_COST_RETAINED_KEYS
    )
    assert sizing.ACCEPTED_REJECTED_RECOVERED_ROWS == 176
    assert sizing.ACCEPTED_UNVERIFIED_RETAINED_OBJECTS == 0
    assert sizing.ACCEPTED_NEW_BINANCE_RAW_BYTES == 20_351_715_427
    assert (
        sizing.ACCEPTED_COMBINED_BYTES - sizing.ACCEPTED_RETAINED_CREDIT_BYTES
        == sizing.ACCEPTED_NEW_BINANCE_RAW_BYTES
    )
    assert sizing.ACCEPTED_PLAN_ACTIONS == {
        "download": 84,
        "reuse_retained": 12,
        "alias": 10,
    }
    assert sum(sizing.ACCEPTED_PLAN_ACTIONS.values()) == sizing.ACCEPTED_PLAN_ENTRIES == 106
    assert sizing.ACCEPTED_SAMPLE_COHORT == 96
    assert len(sizing.ARCHIVE_FAMILIES) == 10
    assert len(sizing.COST_FAMILIES) == 2
    assert len(sizing.PHYSICAL_FAMILIES) == 12
    assert sizing.ACCEPTED_COINALYZE_SUPPORTED_MAPPINGS == 569
    assert sizing.ACCEPTED_COINALYZE_TYPED_GAPS == 202
    assert sizing.ACCEPTED_COINALYZE_PROVENANCE_RECORDS == 5


def test_accepted_authority_loads_with_every_new_pin(accepted: dict[str, Any]) -> None:
    authority = load_sizing_authority(accepted["paths"])
    assert authority.bindings["progress_checkpoint_sha256"]
    assert authority.bindings["listing_checkpoint_sha256"]
    assert authority.bindings["contract_metadata_sha256"]
    assert len(authority.plan_entries) == len(accepted["plan_entries"])


@pytest.mark.parametrize(
    "target",
    ["report", "detail", "lock", "ledger", "source", "cli", "progress", "listing",
     "metadata"],
)
def test_each_pinned_artifact_failure_blocks(
    accepted: dict[str, Any], target: str
) -> None:
    path = accepted["files"][target]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(SizingError):
        load_sizing_authority(accepted["paths"])


@pytest.mark.parametrize("target", ["report", "detail"])
def test_a_pinned_byte_count_blocks_even_when_the_digest_is_repointed(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    """Size is an independent pin, not a by-product of the content digest."""
    path = accepted["files"][target]
    path.write_bytes(path.read_bytes() + b" ")
    pin = {
        "report": "ACCEPTED_REPORT_SHA256",
        "detail": "ACCEPTED_MANIFEST_DETAIL_SHA256",
    }[target]
    monkeypatch.setattr(sizing, pin, _sha256(path.read_bytes()))
    with pytest.raises(SizingError, match="_bytes"):
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


def _credit(
    accepted: dict[str, Any],
    selected: Any,
    cost: Any,
    *,
    report: dict[str, Any] | None = None,
    checkpoint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Re-prove the acquisition credit over the whole requirement, as sizing does."""
    if report is None:
        report = json.loads(accepted["files"]["report"].read_text())
    if checkpoint is None:
        checkpoint = json.loads(accepted["files"]["progress"].read_text())["objects"]
    return sizing.prove_retained_acquisition_credit(
        selected,
        cost,
        report=report,
        checkpoint=checkpoint,
        sample_dir=accepted["paths"].sample_dir,
        sidecar_dir=accepted["paths"].sidecar_dir,
    )


def _requirement(accepted: dict[str, Any]) -> tuple[Any, Any]:
    authority = load_sizing_authority(accepted["paths"])
    selected, _ = resolve_selected_objects(accepted["detail_path"])
    cost, _ = resolve_cost_objects(authority, listing_cache_dir=accepted["listing_cache"])
    return selected, cost


def test_exact_totals_reconcile_before_measurement(accepted: dict[str, Any]) -> None:
    authority = load_sizing_authority(accepted["paths"])
    selected, _ = resolve_selected_objects(accepted["detail_path"])
    cost, _ = resolve_cost_objects(authority, listing_cache_dir=accepted["listing_cache"])
    checkpoint = json.loads(accepted["files"]["progress"].read_text())["objects"]
    credit = _credit(accepted, selected, cost)
    # The credit is every re-proved effective row inside the selected-plus-cost
    # requirement, never the measurement cohort and never the manifest's separate
    # consumable count. Keys, objects, and bytes remain three separate facts.
    assert credit["valid_requirement_keys"] == len(accepted["credited_rows"])
    assert credit["objects"] == len(accepted["credited_objects"])
    assert credit["objects"] < credit["valid_requirement_keys"]
    assert credit["objects"] != len(accepted["cohort_rows"])
    assert credit["bytes"] == sizing.ACCEPTED_RETAINED_CREDIT_BYTES
    assert credit["selected_retained_keys"] == sizing.ACCEPTED_SELECTED_RETAINED_KEYS
    assert credit["cost_retained_keys"] == sizing.ACCEPTED_COST_RETAINED_KEYS
    assert credit["rejected_recovered_rows"] == len(accepted["rejected_keys"])
    assert credit["unverified_objects"] == 0
    assert set(credit["keys"]).isdisjoint(accepted["rejected_keys"])
    assert checkpoint[accepted["rejected_keys"][0]]["status"] == "complete"
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


def _rewrite_checkpoint(
    accepted: dict[str, Any], objects: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Persist a mutated progress checkpoint and re-point only its own pin."""
    path = accepted["files"]["progress"]
    document = json.loads(path.read_text())
    document["objects"] = objects
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    monkeypatch.setattr(
        sizing, "ACCEPTED_PROGRESS_CHECKPOINT_SHA256", _sha256(path.read_bytes())
    )


def _checkpoint(accepted: dict[str, Any]) -> dict[str, Any]:
    return dict(json.loads(accepted["files"]["progress"].read_text())["objects"])


def test_an_ambiguous_recovered_row_earns_no_key_object_or_byte(
    accepted: dict[str, Any],
) -> None:
    selected, cost = _requirement(accepted)
    checkpoint = _checkpoint(accepted)
    rejected = accepted["rejected_keys"][0]
    entry = checkpoint[rejected]
    # The row is not damaged evidence: its bytes and its sidecar both rehash exactly.
    assert entry["recovered_from_retained_bytes"] is True
    assert verify_retained_object(
        rejected,
        entry,
        sample_dir=accepted["paths"].sample_dir,
        sidecar_dir=accepted["paths"].sidecar_dir,
    ) == int(entry["byte_size"])
    credit = _credit(accepted, selected, cost)
    assert rejected not in credit["keys"]
    assert entry["sha256"] not in {
        _sha256(accepted["payloads"][key]) for key in credit["keys"]
    }
    assert credit["bytes"] == sum(
        int(checkpoint[key]["byte_size"])
        for key in {_sha256(accepted["payloads"][k]): k for k in credit["keys"]}.values()
    )


def test_a_fresh_exact_key_with_the_colliding_basename_stays_valid(
    accepted: dict[str, Any],
) -> None:
    selected, cost = _requirement(accepted)
    twin = str(accepted["collision_twin"]["key"])
    rejected = accepted["rejected_keys"][0]
    assert _base(accepted["collision_twin"]) == _base(accepted["ambiguous_row"])
    assert twin != rejected
    credit = _credit(accepted, selected, cost)
    # Ambiguity is a property of basename-only recovery, never of the basename itself.
    assert twin in credit["keys"]
    assert rejected not in credit["keys"]


def test_a_basename_unique_recovery_stays_valid(accepted: dict[str, Any]) -> None:
    selected, cost = _requirement(accepted)
    key = str(accepted["unique_recovered"]["key"])
    checkpoint = _checkpoint(accepted)
    assert checkpoint[key]["recovered_from_retained_bytes"] is True
    credit = _credit(accepted, selected, cost)
    assert key in credit["keys"]
    assert credit["cost_retained_keys"] == sizing.ACCEPTED_COST_RETAINED_KEYS


def test_a_valid_duplicate_binding_adds_a_key_but_no_object_or_byte(
    accepted: dict[str, Any],
) -> None:
    selected, cost = _requirement(accepted)
    first = str(accepted["duplicate_source"]["key"])
    second = str(accepted["duplicate_row"]["key"])
    checkpoint = _checkpoint(accepted)
    assert first != second
    assert checkpoint[first]["sha256"] == checkpoint[second]["sha256"]
    credit = _credit(accepted, selected, cost)
    assert first in credit["keys"] and second in credit["keys"]
    assert credit["valid_requirement_keys"] == credit["objects"] + 1
    assert credit["valid_requirement_keys"] == len(set(credit["keys"]))


def test_an_invalid_duplicate_binding_never_preserves_credit_on_its_own(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    selected, cost = _requirement(accepted)
    first = str(accepted["duplicate_source"]["key"])
    second = str(accepted["duplicate_row"]["key"])
    shared = _sha256(accepted["payloads"][first])
    baseline = _credit(accepted, selected, cost)
    # One binding invalidated: the other still proves the object, so the object and its
    # bytes survive and exactly one logical key is lost.
    checkpoint = _checkpoint(accepted)
    checkpoint[first] = dict(checkpoint[first], sha256="0" * 64)
    partial_report = json.loads(accepted["files"]["report"].read_text())
    partial_summary = partial_report["storage"]["gate2_feasibility"]
    partial_summary["retained_valid_requirement_keys"] -= 1
    partial_summary["unverified_retained_objects"] = 1
    with monkeypatch.context() as patch:
        patch.setattr(
            sizing,
            "ACCEPTED_RETAINED_CREDIT_KEYS",
            sizing.ACCEPTED_RETAINED_CREDIT_KEYS - 1,
        )
        patch.setattr(
            sizing,
            "ACCEPTED_SELECTED_RETAINED_KEYS",
            sizing.ACCEPTED_SELECTED_RETAINED_KEYS - 1,
        )
        patch.setattr(sizing, "ACCEPTED_UNVERIFIED_RETAINED_OBJECTS", 1)
        partial = _credit(
            accepted,
            selected,
            cost,
            report=partial_report,
            checkpoint=checkpoint,
        )
    assert first not in partial["keys"] and second in partial["keys"]
    assert partial["objects"] == baseline["objects"]
    assert partial["bytes"] == baseline["bytes"]
    # Both bindings invalidated: no valid binding remains, so the object and every one
    # of its bytes leave the credit entirely.
    checkpoint[second] = dict(checkpoint[second], sha256="0" * 64)
    gone_report = json.loads(accepted["files"]["report"].read_text())
    gone_summary = gone_report["storage"]["gate2_feasibility"]
    gone_summary["retained_valid_requirement_keys"] -= 2
    gone_summary["retained_verified_credit_objects"] -= 1
    gone_summary["retained_verified_credit_bytes"] -= len(
        accepted["payloads"][first]
    )
    gone_summary["unverified_retained_objects"] = 2
    with monkeypatch.context() as patch:
        patch.setattr(
            sizing,
            "ACCEPTED_RETAINED_CREDIT_KEYS",
            sizing.ACCEPTED_RETAINED_CREDIT_KEYS - 2,
        )
        patch.setattr(
            sizing,
            "ACCEPTED_SELECTED_RETAINED_KEYS",
            sizing.ACCEPTED_SELECTED_RETAINED_KEYS - 2,
        )
        patch.setattr(sizing, "ACCEPTED_UNVERIFIED_RETAINED_OBJECTS", 2)
        patch.setattr(
            sizing,
            "ACCEPTED_RETAINED_CREDIT_OBJECTS",
            sizing.ACCEPTED_RETAINED_CREDIT_OBJECTS - 1,
        )
        patch.setattr(
            sizing,
            "ACCEPTED_RETAINED_CREDIT_BYTES",
            sizing.ACCEPTED_RETAINED_CREDIT_BYTES
            - len(accepted["payloads"][first]),
        )
        gone = _credit(
            accepted,
            selected,
            cost,
            report=gone_report,
            checkpoint=checkpoint,
        )
    assert first not in gone["keys"] and second not in gone["keys"]
    assert gone["objects"] == baseline["objects"] - 1
    assert gone["bytes"] == baseline["bytes"] - len(accepted["payloads"][first])
    assert shared not in {_sha256(accepted["payloads"][key]) for key in gone["keys"]}


def test_the_two_rejected_report_locations_must_agree(accepted: dict[str, Any]) -> None:
    selected, cost = _requirement(accepted)
    report = json.loads(accepted["files"]["report"].read_text())
    rows = report["storage"]["gate2_feasibility"]["rejected_retained_rows"]
    rows[0] = dict(rows[0], key=str(accepted["collision_twin"]["key"]))
    with pytest.raises(SizingError, match="rejected-retained locations disagree"):
        _credit(accepted, selected, cost, report=report)


@pytest.mark.parametrize(
    "field", ["rejected_ambiguous_retained_count", "rejected_retained_row_count"]
)
def test_a_rejected_count_that_disagrees_with_its_own_rows_blocks(
    accepted: dict[str, Any], field: str
) -> None:
    selected, cost = _requirement(accepted)
    report = json.loads(accepted["files"]["report"].read_text())
    if field == "rejected_ambiguous_retained_count":
        report["resume"][field] = int(report["resume"][field]) + 1
    else:
        report["storage"]["gate2_feasibility"][field] = (
            int(report["storage"]["gate2_feasibility"][field]) + 1
        )
    with pytest.raises(SizingError):
        _credit(accepted, selected, cost, report=report)


def test_a_missing_rejected_entry_blocks(accepted: dict[str, Any]) -> None:
    selected, cost = _requirement(accepted)
    report = json.loads(accepted["files"]["report"].read_text())
    report["resume"]["rejected_ambiguous_retained_keys"] = []
    report["resume"]["rejected_ambiguous_retained_count"] = 0
    report["storage"]["gate2_feasibility"]["rejected_retained_rows"] = []
    report["storage"]["gate2_feasibility"]["rejected_retained_row_count"] = 0
    # Dropping the rejected rows contradicts the report's own accepted retained counts.
    # The blocking premise is what matters, not which fail-closed field fires first, so
    # this asserts the block itself and that the unaltered report still proves credit.
    with pytest.raises(SizingError):
        _credit(accepted, selected, cost, report=report)
    intact = _credit(accepted, selected, cost)
    assert intact["rejected_recovered_rows"] == len(accepted["rejected_keys"])


def test_manifest_consumability_is_a_separate_proved_authority(
    accepted: dict[str, Any],
) -> None:
    """The manifest's consumable count is derived, pinned, and kept out of credit."""
    selected, cost = _requirement(accepted)
    objects, counts = resolve_selected_objects(accepted["detail_path"])
    consumable = [item for item in objects if item.consumable]
    assert counts["manifest_consumable_rows"] == len(consumable)
    assert counts["manifest_consumable_rows"] == sizing.ACCEPTED_MANIFEST_CONSUMABLE_ROWS
    assert counts["manifest_consumable_rows"] == len(accepted["consumable_rows"])
    credit = _credit(accepted, selected, cost)
    # The two authorities have different boundaries and different counts.
    assert credit["selected_retained_keys"] != counts["manifest_consumable_rows"]
    assert credit["valid_requirement_keys"] != counts["manifest_consumable_rows"]


def test_a_manifest_consumable_count_that_disagrees_blocks(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sizing,
        "ACCEPTED_MANIFEST_CONSUMABLE_ROWS",
        sizing.ACCEPTED_MANIFEST_CONSUMABLE_ROWS + 1,
    )
    with pytest.raises(SizingError, match="manifest_consumable_rows"):
        resolve_selected_objects(accepted["detail_path"])


def test_a_selected_key_without_the_consumable_flag_still_earns_credit(
    accepted: dict[str, Any],
) -> None:
    """ADR-0023: Gate-2 credit is re-proved evidence, not manifest consumability."""
    selected, cost = _requirement(accepted)
    unconsumable = [str(row["key"]) for row in accepted["unconsumable_credited"]]
    assert unconsumable
    manifest = {item.key: item.consumable for item in selected}
    assert all(manifest[key] is False for key in unconsumable)
    credit = _credit(accepted, selected, cost)
    assert set(unconsumable) <= set(credit["keys"])
    # Those keys are selected credit, never cost credit.
    assert credit["selected_retained_keys"] >= len(unconsumable)
    assert credit["selected_retained_keys"] == sizing.ACCEPTED_SELECTED_RETAINED_KEYS
    assert credit["cost_retained_keys"] == sizing.ACCEPTED_COST_RETAINED_KEYS


def test_credit_keys_are_classified_by_requirement_membership(
    accepted: dict[str, Any],
) -> None:
    """Each side of the split comes from actual membership, never from subtraction."""
    selected, cost = _requirement(accepted)
    selected_keys = {item.key for item in selected}
    cost_keys = {item.key for item in cost}
    assert not selected_keys & cost_keys
    credit = _credit(accepted, selected, cost)
    credited = set(credit["keys"])
    assert credited <= selected_keys | cost_keys
    assert len(credited & selected_keys) == credit["selected_retained_keys"]
    assert len(credited & cost_keys) == credit["cost_retained_keys"]
    assert (
        credit["selected_retained_keys"] + credit["cost_retained_keys"]
        == credit["valid_requirement_keys"]
    )


def test_a_key_in_both_requirement_sets_blocks(accepted: dict[str, Any]) -> None:
    selected, cost = _requirement(accepted)
    with pytest.raises(SizingError, match="both the selected and the cost requirement"):
        _credit(accepted, selected, tuple(cost) + (selected[0],))


def test_the_report_retained_summary_is_proved_field_by_field(
    accepted: dict[str, Any],
) -> None:
    selected, cost = _requirement(accepted)
    report = json.loads(accepted["files"]["report"].read_text())
    summary = sizing.prove_report_retained_summary(report)
    assert set(summary) == set(sizing.ACCEPTED_RETAINED_SUMMARY_FIELDS)
    assert summary["retained_valid_requirement_keys"] == (
        sizing.ACCEPTED_RETAINED_CREDIT_KEYS
    )
    assert summary["retained_verified_credit_objects"] == (
        sizing.ACCEPTED_RETAINED_CREDIT_OBJECTS
    )
    assert summary["retained_verified_credit_bytes"] == (
        sizing.ACCEPTED_RETAINED_CREDIT_BYTES
    )
    assert summary["unverified_retained_objects"] == 0
    assert summary["rejected_retained_row_count"] == len(accepted["rejected_keys"])
    # The proved summary travels with the credit the consumer acts on.
    assert _credit(accepted, selected, cost)["report_summary"] == summary


@pytest.mark.parametrize("field", sorted(sizing.ACCEPTED_RETAINED_SUMMARY_FIELDS))
@pytest.mark.parametrize("replacement", ["increment", "decrement", "text", "boolean"])
def test_each_altered_retained_summary_field_blocks(
    accepted: dict[str, Any], field: str, replacement: str
) -> None:
    """Every accepted retained quantity is independently fail-closed by its own name."""
    selected, cost = _requirement(accepted)
    report = json.loads(accepted["files"]["report"].read_text())
    feasibility = report["storage"]["gate2_feasibility"]
    current = int(feasibility[field])
    feasibility[field] = {
        "increment": current + 1,
        "decrement": current - 1,
        "text": str(current),
        "boolean": True,
    }[replacement]
    with pytest.raises(SizingError) as failure:
        sizing.prove_report_retained_summary(report)
    assert field in str(failure.value)
    with pytest.raises(SizingError):
        _credit(accepted, selected, cost, report=report)


def test_an_altered_retained_summary_blocks_before_any_publication(
    accepted: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The summary is proved before measurement, so nothing reaches publication."""
    path = accepted["files"]["report"]
    report = json.loads(path.read_text())
    feasibility = report["storage"]["gate2_feasibility"]
    feasibility["retained_verified_credit_bytes"] = (
        int(feasibility["retained_verified_credit_bytes"]) + 1
    )
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    monkeypatch.setattr(sizing, "ACCEPTED_REPORT_SHA256", _sha256(path.read_bytes()))
    monkeypatch.setattr(sizing, "ACCEPTED_REPORT_BYTES", path.stat().st_size)
    receipt_path = tmp_path / "180_receipt.json"
    with pytest.raises(SizingError, match="retained_verified_credit_bytes"):
        _run(accepted, tmp_path, receipt_path=receipt_path)
    assert not receipt_path.exists()
    assert not list(tmp_path.rglob("*.parquet"))


@pytest.mark.parametrize(
    "damage",
    ["missing_object", "corrupt_object", "missing_sidecar", "corrupt_sidecar",
     "wrong_sidecar_name", "wrong_byte_size", "missing_byte_size", "zero_byte_size",
     "negative_byte_size", "text_byte_size", "boolean_byte_size"],
)
def test_damaged_retained_evidence_blocks_before_any_publication(
    accepted: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    damage: str,
) -> None:
    selected, cost = _requirement(accepted)
    key = str(accepted["collision_twin"]["key"])
    checkpoint = _checkpoint(accepted)
    entry = dict(checkpoint[key])
    object_path = accepted["paths"].sample_dir / str(entry["sha256"])
    sidecar_path = Path(str(entry["provider_checksum_path"]))
    if damage == "missing_object":
        object_path.unlink()
    elif damage == "corrupt_object":
        object_path.write_bytes(object_path.read_bytes() + b"x")
    elif damage == "missing_sidecar":
        sidecar_path.unlink()
    elif damage == "corrupt_sidecar":
        sidecar_path.write_bytes(b"0" * 64 + b"  " + _base(accepted["collision_twin"]).encode())
    elif damage == "wrong_sidecar_name":
        sidecar_path.write_bytes(
            f"{entry['sha256']}  not-{_base(accepted['collision_twin'])}\n".encode()
        )
    elif damage == "missing_byte_size":
        # The declared size is proved, so its absence is a block and never a default.
        entry.pop("byte_size")
        checkpoint[key] = entry
        _rewrite_checkpoint(accepted, checkpoint, monkeypatch)
    else:
        entry["byte_size"] = {
            "wrong_byte_size": int(entry["byte_size"]) + 1,
            "zero_byte_size": 0,
            "negative_byte_size": -int(entry["byte_size"]),
            "text_byte_size": str(entry["byte_size"]),
            "boolean_byte_size": True,
        }[damage]
        checkpoint[key] = entry
        _rewrite_checkpoint(accepted, checkpoint, monkeypatch)
    with pytest.raises(SizingError):
        _credit(accepted, selected, cost, checkpoint=checkpoint)
    # The same damage stops the whole sizing flow before anything is published.
    receipt_path = tmp_path / "180_receipt.json"
    with pytest.raises(SizingError):
        _run(accepted, tmp_path, receipt_path=receipt_path)
    assert not receipt_path.exists()
    assert not list(tmp_path.rglob("*.parquet"))


def test_the_receipt_publishes_the_adr0023_credit_decomposition(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    receipt = _run(accepted, tmp_path)["receipt"]
    credit = receipt["physical_inputs"]["retained_credit"]
    assert credit["valid_requirement_keys"] == sizing.ACCEPTED_RETAINED_CREDIT_KEYS
    assert credit["objects"] == sizing.ACCEPTED_RETAINED_CREDIT_OBJECTS
    assert credit["bytes"] == sizing.ACCEPTED_RETAINED_CREDIT_BYTES
    assert credit["selected_retained_keys"] == sizing.ACCEPTED_SELECTED_RETAINED_KEYS
    assert credit["cost_retained_keys"] == sizing.ACCEPTED_COST_RETAINED_KEYS
    assert credit["rejected_recovered_rows"] == len(accepted["rejected_keys"])
    assert credit["unverified_objects"] == 0
    assert (
        credit["selected_retained_keys"] + credit["cost_retained_keys"]
        == credit["valid_requirement_keys"]
    )
    # The three quantities stay distinct in the published evidence.
    assert credit["objects"] < credit["valid_requirement_keys"]
    assert set(credit["keys"]).isdisjoint(accepted["rejected_keys"])
    assert receipt["physical_inputs"]["retained_credit_objects"] == credit["objects"]
    assert receipt["physical_inputs"]["retained_credit_bytes"] == credit["bytes"]
    # The cohort is a measurement set and is never confused with acquisition credit.
    assert receipt["cohort"]["unique_samples"] != credit["valid_requirement_keys"]
    # The manifest's separate publication fact is published separately, and no credit
    # quantity is recoverable by subtracting it from the credit total.
    consumable = receipt["physical_inputs"]["manifest_consumable_rows"]
    assert consumable == sizing.ACCEPTED_MANIFEST_CONSUMABLE_ROWS
    assert consumable == len(accepted["consumable_rows"])
    assert consumable != credit["selected_retained_keys"]
    assert credit["valid_requirement_keys"] - consumable != credit["cost_retained_keys"]


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
    import inspect

    huge = 2**53
    # These two ratios are indistinguishable in float64 and must still order exactly.
    assert ratio_exceeds((huge + 1, huge), (huge, huge))
    assert not ratio_exceeds((huge, huge), (huge + 1, huge))
    assert ceil_div((huge + 1) * 7, 3) == ((huge + 1) * 7 + 2) // 3
    with pytest.raises(SizingError):
        ratio_exceeds((1, 0), (1, 1))
    source = inspect.getsource(ratio_exceeds) + inspect.getsource(ceil_div)
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert "float(" not in stripped


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


def _provenance_record(accepted: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """One record in the exact accepted shape, before any deliberate alteration."""
    report = json.loads(accepted["files"]["report"].read_text())
    record = dict(report["coinalyze"]["provenance"][0])
    record.update(overrides)
    return record


def _coinalyze_report(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch, mutate: Any
) -> Any:
    """Rewrite the pinned report's Coinalyze block and re-point only its own pins."""
    path = accepted["files"]["report"]
    report = json.loads(path.read_text())
    mutate(report["coinalyze"])
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    monkeypatch.setattr(sizing, "ACCEPTED_REPORT_SHA256", _sha256(path.read_bytes()))
    monkeypatch.setattr(sizing, "ACCEPTED_REPORT_BYTES", path.stat().st_size)
    return load_sizing_authority(accepted["paths"])


def test_the_accepted_header_name_provenance_resolves(accepted: dict[str, Any]) -> None:
    """A header *name* is safe metadata; the accepted shape must not be mistaken for a
    stored credential."""
    authority = load_sizing_authority(accepted["paths"])
    block = dict(authority.report["coinalyze"])
    assert sizing.prove_coinalyze_request_framing(block) == {
        "key_location": "header",
        "key_present": True,
        "query_contains_key": False,
    }
    for record in block["provenance"]:
        assert record["header_names"] == ["api_key"]
        assert set(record) == set(sizing.ACCEPTED_COINALYZE_PROVENANCE_FIELDS)
        sizing.prove_coinalyze_provenance_record(
            record, endpoint=str(record["path"]), context={}
        )
    evidence = resolve_coinalyze_evidence(
        authority, cache_dir=accepted["coinalyze_cache"]
    )
    assert len(evidence) == sizing.ACCEPTED_COINALYZE_PROVENANCE_RECORDS


@pytest.mark.parametrize(
    "framing",
    [
        {"key_location": "query"},
        {"key_location": ""},
        {"key_present": False},
        {"key_present": "true"},
        {"query_contains_key": True},
        {"query_contains_key": "false"},
    ],
)
def test_altered_report_level_framing_blocks(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch, framing: dict[str, Any]
) -> None:
    field = next(iter(framing))
    authority = _coinalyze_report(
        accepted, monkeypatch, lambda block: block.update(framing)
    )
    with pytest.raises(SizingError, match=field) as failure:
        resolve_coinalyze_evidence(authority, cache_dir=accepted["coinalyze_cache"])
    assert "provenance" not in failure.value.context


@pytest.mark.parametrize(
    "header_names",
    [["Authorization"], ["api_key", "authorization"], [], ["API_KEY"], "api_key", [1]],
)
def test_wrong_missing_or_extra_header_names_block(
    accepted: dict[str, Any], header_names: Any
) -> None:
    record = _provenance_record(accepted, header_names=header_names)
    with pytest.raises(SizingError, match="header_names"):
        sizing.prove_coinalyze_provenance_record(
            record, endpoint="/future-markets", context={}
        )


def test_a_missing_header_names_field_blocks(accepted: dict[str, Any]) -> None:
    record = _provenance_record(accepted)
    record.pop("header_names")
    with pytest.raises(SizingError, match="missing an accepted field") as failure:
        sizing.prove_coinalyze_provenance_record(
            record, endpoint="/future-markets", context={}
        )
    assert failure.value.context["missing_fields"] == ["header_names"]


@pytest.mark.parametrize("name", ["api_key", "apiKey", "api-key", "API-KEY", "ApI_kEy"])
def test_a_credential_query_parameter_blocks_even_when_redacted(
    accepted: dict[str, Any], name: str
) -> None:
    record = _provenance_record(accepted)
    record["params"] = {"symbols": "BTCUSDT_PERP.A", name: "<redacted>"}
    with pytest.raises(SizingError, match="credential query parameter") as failure:
        sizing.prove_coinalyze_provenance_record(
            record, endpoint="/future-markets", context={}
        )
    # The offending name is structural evidence; its value is never read or reported.
    assert failure.value.context["parameter_names"] == [name]
    assert "<redacted>" not in str(failure.value)


@pytest.mark.parametrize(
    "field", ["headers", "header_values", "authorization", "credential", "surprise"]
)
def test_an_unrecognized_provenance_field_blocks_without_echoing_it(
    accepted: dict[str, Any], field: str
) -> None:
    secret = "Bearer never-print-this-value"
    record = _provenance_record(accepted)
    record[field] = {"api_key": secret} if field.startswith("header") else secret
    with pytest.raises(SizingError, match="unrecognized field") as failure:
        sizing.prove_coinalyze_provenance_record(
            record, endpoint="/future-markets", context={}
        )
    assert failure.value.context["unexpected_fields"] == [field]
    rendered = str(failure.value) + json.dumps(failure.value.context, sort_keys=True)
    assert secret not in rendered
    assert "never-print-this-value" not in rendered


def test_a_non_string_parameter_map_blocks(accepted: dict[str, Any]) -> None:
    record = _provenance_record(accepted)
    record["params"] = {"symbols": ["BTCUSDT_PERP.A"]}
    with pytest.raises(SizingError, match="string-to-string parameter map"):
        sizing.prove_coinalyze_provenance_record(
            record, endpoint="/future-markets", context={}
        )


def test_resolved_evidence_and_receipt_carry_no_request_metadata(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    evidence = resolve_coinalyze_evidence(
        authority, cache_dir=accepted["coinalyze_cache"]
    )
    for item in evidence:
        # The evidence type has no field that could carry request metadata at all.
        assert not set(item.__slots__) & {
            "params", "header_names", "headers", "api_key"
        }
        assert set(item.to_dict()) == {
            "endpoint", "role", "sha256", "byte_size", "content_path"
        }
    rendered = sizing.canonical_json(_run(accepted, tmp_path)["receipt"]).decode()
    for forbidden in ("header_names", "api_key", "apiKey", "<redacted>", "params"):
        assert forbidden not in rendered
    # Provider identities are legitimate published evidence; the *request* that carried
    # them is not. The joined parameter value never reaches a published byte.
    report = json.loads(accepted["files"]["report"].read_text())
    joined = report["coinalyze"]["provenance"][0]["params"]["symbols"]
    assert "," in joined
    assert joined not in rendered
    assert "provenance_source" not in rendered
    assert "retrieved_at" not in rendered


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


def _coinalyze(accepted: dict[str, Any]) -> dict[str, Any]:
    """Resolve the accepted Coinalyze evidence and prove its identity binding once."""
    authority = load_sizing_authority(accepted["paths"])
    evidence = resolve_coinalyze_evidence(
        authority, cache_dir=accepted["coinalyze_cache"]
    )
    inventory = next(item for item in evidence if item.role == "future_market_inventory")
    identities = sizing.prove_coinalyze_identity_map(authority, inventory=inventory)
    supported, unmapped = coinalyze_symbol_sets(
        authority, inventory=inventory, identities=identities
    )
    lifecycles, cutoff = coinalyze_lifecycles(authority, supported=supported)
    return {
        "authority": authority,
        "evidence": evidence,
        "inventory": inventory,
        "identities": identities,
        "supported": supported,
        "unmapped": unmapped,
        "lifecycles": lifecycles,
        "cutoff": cutoff,
    }


def _with_inventory(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, Any]]
) -> Any:
    """Re-publish the retained inventory body and re-point only the pins it moves.

    The report's declared market counts follow the body that is actually published, so a
    test breaks exactly the one binding it means to break and nothing else.
    """
    body = json.dumps(rows).encode("utf-8")
    digest = _sha256(body)
    (accepted["coinalyze_cache"] / digest).write_bytes(body)
    declared = sum(
        1
        for row in rows
        if row.get("exchange") == "A" and row.get("is_perpetual") is True
    )
    path = accepted["files"]["report"]
    report = json.loads(path.read_text())
    report["coinalyze"]["binance_perpetual_market_count"] = declared
    report["coinalyze"]["native_identity_validated_markets"] = declared
    for record in report["coinalyze"]["provenance"]:
        if record["path"] == "/future-markets":
            record["sha256"] = digest
            record["byte_size"] = len(body)
            record["content_path"] = str(accepted["coinalyze_cache"] / digest)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    monkeypatch.setattr(sizing, "ACCEPTED_REPORT_SHA256", _sha256(path.read_bytes()))
    monkeypatch.setattr(sizing, "ACCEPTED_REPORT_BYTES", path.stat().st_size)
    authority = load_sizing_authority(accepted["paths"])
    evidence = resolve_coinalyze_evidence(
        authority, cache_dir=accepted["coinalyze_cache"]
    )
    inventory = next(item for item in evidence if item.role == "future_market_inventory")
    return authority, inventory


def test_the_inventory_binds_provider_and_native_identities(
    accepted: dict[str, Any],
) -> None:
    """The real BTC/ETH-shaped success path, in both namespaces at once."""
    resolved = _coinalyze(accepted)
    identities = resolved["identities"]
    for native in accepted["supported_natives"] + accepted["extra_natives"]:
        provider = accepted["provider_of"][native]
        assert identities.provider_to_native[provider] == native
        assert identities.native_to_provider[native] == provider
        assert provider != native
    # Only Binance perpetuals are bound: another venue and a dated future are not.
    assert "BTCUSD_PERP.F" not in identities.provider_to_native
    assert "BTCUSDT_240628.A" not in identities.provider_to_native
    assert identities.perpetual_markets == len(accepted["supported_natives"]) + len(
        accepted["extra_natives"]
    )
    # The inventory validates more markets than this projection ever counts.
    assert identities.perpetual_markets > len(resolved["supported"])
    assert set(resolved["supported"]) < set(identities.native_to_provider)


@pytest.mark.parametrize(
    "field", ["binance_perpetual_market_count", "native_identity_validated_markets"]
)
def test_the_report_inventory_count_must_match_the_proved_map(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    resolved = _coinalyze(accepted)
    authority = _coinalyze_report(
        accepted, monkeypatch, lambda block: block.update({field: 99})
    )
    with pytest.raises(SizingError, match=field):
        sizing.prove_coinalyze_identity_map(
            authority, inventory=resolved["inventory"]
        )


def test_a_non_integer_inventory_count_blocks(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    resolved = _coinalyze(accepted)
    authority = _coinalyze_report(
        accepted,
        monkeypatch,
        lambda block: block.update({"binance_perpetual_market_count": "6"}),
    )
    with pytest.raises(SizingError, match="positive inventory market count"):
        sizing.prove_coinalyze_identity_map(
            authority, inventory=resolved["inventory"]
        )


@pytest.mark.parametrize("shape", ["substituted_binding", "missing_supported_mapping"])
def test_same_count_with_a_broken_supported_binding_blocks(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch, shape: str
) -> None:
    """The market count still agrees; the supported native no longer has a binding."""
    native = accepted["supported_natives"][0]
    rows = [dict(row) for row in accepted["inventory_rows"]]
    if shape == "substituted_binding":
        for row in rows:
            if row.get("symbol") == accepted["provider_of"][native]:
                row["symbol_on_exchange"] = "OTHERUSDT"
    else:
        rows = [
            row for row in rows if row.get("symbol") != accepted["provider_of"][native]
        ]
        rows.append(_market_row("LTCUSDT_PERP.A", "LTCUSDT"))
    authority, inventory = _with_inventory(accepted, monkeypatch, rows)
    identities = sizing.prove_coinalyze_identity_map(authority, inventory=inventory)
    assert identities.perpetual_markets == len(accepted["supported_natives"]) + len(
        accepted["extra_natives"]
    )
    with pytest.raises(SizingError, match="no proved native inventory binding"):
        coinalyze_symbol_sets(authority, inventory=inventory, identities=identities)


@pytest.mark.parametrize(
    ("shape", "message"),
    [
        ("repeated_row", "repeats a Binance perpetual market"),
        ("duplicate_provider", "binds two native identities"),
        ("duplicate_native", "binds two Coinalyze provider identities"),
        ("missing_native", "has no symbol_on_exchange"),
        ("missing_provider", "has no provider symbol"),
        ("non_boolean_perpetual", "is_perpetual"),
    ],
)
def test_broken_inventory_rows_block(
    accepted: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    shape: str,
    message: str,
) -> None:
    native = accepted["supported_natives"][0]
    provider = accepted["provider_of"][native]
    rows = [dict(row) for row in accepted["inventory_rows"]]
    if shape == "repeated_row":
        rows.append(_market_row(provider, native))
    elif shape == "duplicate_provider":
        rows.append(_market_row(provider, "OTHERUSDT"))
    elif shape == "duplicate_native":
        rows.append(_market_row("OTHER_PERP.A", native))
    elif shape == "missing_native":
        rows.append(dict(_market_row("NEW_PERP.A", "NEWUSDT"), symbol_on_exchange=""))
    elif shape == "missing_provider":
        rows.append(dict(_market_row("NEW_PERP.A", "NEWUSDT"), symbol=""))
    else:
        rows.append(dict(_market_row("NEW_PERP.A", "NEWUSDT"), is_perpetual="true"))
    authority, inventory = _with_inventory(accepted, monkeypatch, rows)
    with pytest.raises(SizingError, match=message):
        sizing.prove_coinalyze_identity_map(authority, inventory=inventory)


@pytest.mark.parametrize("shape", ["wrong_exchange", "not_perpetual"])
def test_a_supported_native_present_only_as_an_excluded_row_blocks(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch, shape: str
) -> None:
    native = accepted["supported_natives"][0]
    provider = accepted["provider_of"][native]
    rows = []
    for row in accepted["inventory_rows"]:
        item = dict(row)
        if item.get("symbol") == provider:
            if shape == "wrong_exchange":
                item["exchange"] = "F"
            else:
                item["is_perpetual"] = False
        rows.append(item)
    authority, inventory = _with_inventory(accepted, monkeypatch, rows)
    identities = sizing.prove_coinalyze_identity_map(authority, inventory=inventory)
    assert native not in identities.native_to_provider
    with pytest.raises(SizingError, match="no proved native inventory binding"):
        coinalyze_symbol_sets(authority, inventory=inventory, identities=identities)


def test_a_retained_provider_maps_to_its_native_lifecycle_bounds(
    accepted: dict[str, Any],
) -> None:
    resolved = _coinalyze(accepted)
    native = accepted["anchor_natives"][0]
    provider = accepted["provider_of"][native]
    # The lifecycle dictionary is keyed natively and holds no provider identity.
    assert native in resolved["lifecycles"]
    assert provider not in resolved["lifecycles"]
    assert resolved["identities"].native_for(provider, context={}) == native
    measured = measure_liquidation_response(
        _liquidation_body([provider], 3), endpoint="/liquidation-history"
    )
    covered = sizing.validate_retained_liquidation_coverage(
        measured,
        supported=resolved["supported"],
        lifecycles=resolved["lifecycles"],
        identities=resolved["identities"],
        endpoint="/liquidation-history",
    )
    assert covered["retained_native_symbols"] == [native]
    assert covered["points_per_native_symbol"][native] == 3


@pytest.mark.parametrize("shape", ["native_string", "unknown_provider"])
def test_a_retained_series_outside_the_provider_namespace_blocks(
    accepted: dict[str, Any], shape: str
) -> None:
    resolved = _coinalyze(accepted)
    symbol = (
        accepted["anchor_natives"][0] if shape == "native_string" else "NOSUCH_PERP.A"
    )
    measured = measure_liquidation_response(
        _liquidation_body([symbol], 3), endpoint="/liquidation-history"
    )
    with pytest.raises(SizingError, match="absent from the accepted inventory"):
        sizing.validate_retained_liquidation_coverage(
            measured,
            supported=resolved["supported"],
            lifecycles=resolved["lifecycles"],
            identities=resolved["identities"],
            endpoint="/liquidation-history",
        )


def test_a_duplicate_retained_series_blocks(accepted: dict[str, Any]) -> None:
    resolved = _coinalyze(accepted)
    provider = accepted["provider_of"][accepted["anchor_natives"][0]]
    measured = measure_liquidation_response(
        _liquidation_body([provider, provider], 3), endpoint="/liquidation-history"
    )
    with pytest.raises(SizingError, match="repeats a provider series"):
        sizing.validate_retained_liquidation_coverage(
            measured,
            supported=resolved["supported"],
            lifecycles=resolved["lifecycles"],
            identities=resolved["identities"],
            endpoint="/liquidation-history",
        )


def test_two_provider_identities_colliding_onto_one_native_block(
    accepted: dict[str, Any],
) -> None:
    """The coverage guard holds even if a collision ever reached the mapping itself."""
    resolved = _coinalyze(accepted)
    native = accepted["anchor_natives"][0]
    provider = accepted["provider_of"][native]
    colliding = sizing.CoinalyzeIdentityMap(
        provider_to_native={provider: native, "ALIAS_PERP.A": native},
        native_to_provider={native: provider},
        perpetual_markets=1,
    )
    measured = measure_liquidation_response(
        _liquidation_body([provider, "ALIAS_PERP.A"], 3),
        endpoint="/liquidation-history",
    )
    with pytest.raises(SizingError, match="collide onto one native symbol"):
        sizing.validate_retained_liquidation_coverage(
            measured,
            supported=resolved["supported"],
            lifecycles=resolved["lifecycles"],
            identities=colliding,
            endpoint="/liquidation-history",
        )


def test_the_accepted_anchor_identity_is_re_proved(accepted: dict[str, Any]) -> None:
    resolved = _coinalyze(accepted)
    providers = [accepted["provider_of"][n] for n in accepted["anchor_natives"]]
    proved = sizing.prove_coinalyze_anchor_identity(
        resolved["authority"],
        identities=resolved["identities"],
        retained_provider_symbols=providers,
    )
    assert proved["anchor_native_symbols"] == sorted(accepted["anchor_natives"])
    assert proved["anchor_provider_symbols"] == sorted(providers)
    assert proved["retained_provider_symbols"] == sorted(providers)


@pytest.mark.parametrize(
    ("shape", "message"),
    [
        ("anchor_symbols", "anchor symbols disagree"),
        ("requested_symbols", "requested symbols disagree"),
        ("matched_markets", "matched markets disagree"),
        ("on_exchange", "anchor_identity.symbol_on_exchange"),
        ("provider_symbol", "absent from the accepted inventory"),
        ("repeated_anchor", "repeats an anchor identity"),
    ],
)
def test_anchor_identity_disagreements_block(
    accepted: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    shape: str,
    message: str,
) -> None:
    resolved = _coinalyze(accepted)
    providers = [accepted["provider_of"][n] for n in accepted["anchor_natives"]]

    def _mutate(block: dict[str, Any]) -> None:
        if shape == "anchor_symbols":
            block["anchor_symbols"] = ["SOLUSDT"]
        elif shape == "requested_symbols":
            block["requested_symbols"] = ["SOLUSDT_PERP.A"]
        elif shape == "matched_markets":
            block["matched_markets"] = ["SOLUSDT_PERP.A"]
        elif shape == "on_exchange":
            block["anchor_identity"][0]["symbol_on_exchange"] = "OTHERUSDT"
        elif shape == "provider_symbol":
            block["anchor_identity"][0]["provider_symbol"] = "NOSUCH_PERP.A"
        else:
            block["anchor_identity"] = [dict(block["anchor_identity"][0])] * 2

    authority = _coinalyze_report(accepted, monkeypatch, _mutate)
    with pytest.raises(SizingError, match=message):
        sizing.prove_coinalyze_anchor_identity(
            authority,
            identities=resolved["identities"],
            retained_provider_symbols=providers,
        )


def test_a_retained_response_that_disagrees_with_the_anchors_blocks(
    accepted: dict[str, Any],
) -> None:
    resolved = _coinalyze(accepted)
    with pytest.raises(SizingError, match="disagrees with the accepted anchors"):
        sizing.prove_coinalyze_anchor_identity(
            resolved["authority"],
            identities=resolved["identities"],
            retained_provider_symbols=[
                accepted["provider_of"][accepted["anchor_natives"][0]]
            ],
        )


def test_the_receipt_carries_both_identity_namespaces(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    receipt = _run(accepted, tmp_path)["receipt"]
    block = receipt["coinalyze"]
    providers = sorted(accepted["provider_of"][n] for n in accepted["anchor_natives"])
    assert block["retained_provider_symbols"] == providers
    assert block["retained_native_symbols"] == sorted(accepted["anchor_natives"])
    assert block["retained_covered_symbols"] == len(accepted["anchor_natives"])
    assert "retained_symbols" not in block
    # Supported sets, lifecycles, and partitions stay native and unchanged.
    assert block["supported_native_symbols"] == sorted(accepted["supported_natives"])
    assert not any(
        symbol.endswith("_PERP.A") for symbol in block["supported_native_symbols"]
    )
    assert block["identity_map"]["binance_perpetual_markets"] == len(
        accepted["supported_natives"]
    ) + len(accepted["extra_natives"])
    assert block["anchor_identity"]["anchor_provider_symbols"] == providers
    assert block["anchor_identity"]["anchor_native_symbols"] == sorted(
        accepted["anchor_natives"]
    )
    assert block["supported_mappings"] == len(accepted["supported_natives"])
    assert block["liquidation_receipts"] == len(accepted["supported_natives"])
    assert block["partition_count"] > 0


def test_supported_symbol_sets_are_compared_not_counted(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    resolved = _coinalyze(accepted)
    inventory = resolved["inventory"]
    identities = resolved["identities"]
    assert list(resolved["supported"]) == sorted(accepted["supported"])
    assert list(resolved["unmapped"]) == sorted(accepted["unmapped"])
    # The supported set is Binance-native; no provider identity belongs in it.
    assert not any(symbol.endswith("_PERP.A") for symbol in resolved["supported"])

    # Same counts, different symbols: a fabricated set no longer satisfies the gate.
    report = json.loads(accepted["files"]["report"].read_text())
    report["coinalyze"]["universe_support"]["supported_symbols"] = [
        f"FAKE{index}USDT" for index in range(len(accepted["supported"]))
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
    with pytest.raises(SizingError, match="no proved native inventory binding"):
        coinalyze_symbol_sets(
            substituted, inventory=inventory, identities=identities
        )


def test_lifecycles_come_from_accepted_evidence_and_block_when_absent(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    lifecycles, cutoff = coinalyze_lifecycles(authority, supported=accepted["supported"])
    assert cutoff == _CUTOFF
    # Lifecycles are keyed by Binance-native identity, exactly as the snapshot is.
    assert set(lifecycles) == set(accepted["supported_natives"])
    for first, last in lifecycles.values():
        assert last >= first

    metadata = json.loads(accepted["files"]["metadata"].read_text())
    metadata["symbol_snapshot"].pop(accepted["supported_natives"][0])
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
    resolved = _coinalyze(accepted)
    supported = resolved["supported"]
    lifecycles = resolved["lifecycles"]
    projection = project_coinalyze(
        evidence=resolved["evidence"],
        supported=supported,
        unmapped=resolved["unmapped"],
        lifecycles=lifecycles,
        identities=resolved["identities"],
        staging=tmp_path,
    )
    # Envelopes are measured under native identity and name their provider identity.
    for envelope in projection.envelopes:
        assert envelope["venue_symbol"] == envelope["native_symbol"]
        assert envelope["provider_symbol"] == accepted["provider_of"][
            envelope["native_symbol"]
        ]
    assert sorted(item["native_symbol"] for item in projection.envelopes) == sorted(
        accepted["anchor_natives"]
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
    provider, tokens = measured["series"][0]
    envelope = write_liquidation_envelope(
        symbol="BTCUSDT",
        provider_symbol=provider,
        endpoint="/liquidation-history",
        tokens=tokens,
        destination=tmp_path / "liq.parquet",
    )
    # The envelope records the venue's native identity and the provider's separately.
    assert envelope["venue_symbol"] == "BTCUSDT"
    assert envelope["native_symbol"] == "BTCUSDT"
    assert envelope["provider_symbol"] == "BTCUSDT_PERP.A"
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
            + counts["projected_coinalyze_receipts"]
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
    resolved = _coinalyze(accepted)
    anchor = accepted["provider_of"][accepted["anchor_natives"][0]]
    if tamper == "unsupported_symbol":
        # A real Binance perpetual the inventory binds, but outside the supported set.
        body = _liquidation_body([accepted["provider_of"][accepted["extra_natives"][0]]], 3)
    elif tamper == "outside_lifecycle":
        body = json.dumps(
            [{"symbol": anchor, "history": [{"t": 1_000_000, "l": "1", "s": "2"}]}]
        ).encode("utf-8")
    else:
        body = json.dumps(
            [
                {
                    "symbol": anchor,
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
            supported=resolved["supported"],
            lifecycles=resolved["lifecycles"],
            identities=resolved["identities"],
            endpoint="/liquidation-history",
        )


def test_repeated_retained_days_are_credited_once(accepted: dict[str, Any]) -> None:
    resolved = _coinalyze(accepted)
    native = accepted["anchor_natives"][0]
    provider = accepted["provider_of"][native]
    measured = measure_liquidation_response(
        _liquidation_body([provider], 4), endpoint="/liquidation-history"
    )
    covered = sizing.validate_retained_liquidation_coverage(
        measured,
        supported=resolved["supported"],
        lifecycles=resolved["lifecycles"],
        identities=resolved["identities"],
        endpoint="/liquidation-history",
    )
    # Both namespaces are retained explicitly and separately named.
    assert covered["retained_provider_symbols"] == [provider]
    assert covered["retained_native_symbols"] == [native]
    assert covered["identity_pairs"] == [
        {"provider_symbol": provider, "native_symbol": native}
    ]
    assert covered["unique_in_lifecycle_points"] == 4
    assert covered["points_per_native_symbol"] == {native: 4}


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
    with pytest.raises(
        SizingError,
        match="symbolic link|already occupies|not a regular file",
    ):
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
    with pytest.raises(
        SizingError, match="not a regular file|escapes its evidence root"
    ):
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
