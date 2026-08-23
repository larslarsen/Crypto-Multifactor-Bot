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
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

import pyarrow as pa
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
    group_objects,
    load_sizing_authority,
    measure_liquidation_response,
    measure_partition_manifest,
    measure_typed_envelope,
    operating_reserve_bytes,
    project_coinalyze,
    REQUIRED_PRODUCTS,
    bind_sample_lineage,
    contribution,
    contributions_for_family,
    contributions_for_product,
    project_typed_partitions,
    prove_product_contract,
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

    sample_records: list[dict[str, Any]] = []
    alias_keys: list[str] = []
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
        # Half the retained objects carry the checkpoint's real `retrieval_time`; the
        # other half honestly have none, and must stay unknown rather than invented.
        if len(checkpoint_objects) % 2 == 0:
            entry["retrieval_time"] = "2026-08-21T00:00:00+00:00"
        checkpoint_objects[key] = entry
        record = {
            "key": key,
            "family": family,
            "symbol": row["symbol"],
            "product": "binance_usdm_bar_1h",
            "products": ["binance_usdm_bar_1h"],
            "regime": "in_sample",
            "sha256": digest,
            "byte_size": len(payload),
            "availability_semantics": "source_object_listing_time_unknown",
            "retrieval_time": str(entry.get("retrieval_time") or ""),
            "source_available_at": None,
        }
        sample_records.append(record)
        # ADR-0025 section 4: some keys legitimately appear in a second sample regime
        # with identical lineage. Those aliases fold; they must not be rejected.
        if len(sample_records) % 3 == 1:
            sample_records.append(
                {**record, "regime": "out_of_sample", "product": "binance_usdm_bar_1h"}
            )
            alias_keys.append(key)
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
    accepted_membership = [
        (native, "USDT", "USDT", native[:-4]) for native in supported_natives
    ] + [
        # An accepted contract whose margin and settlement are not USDT.
        ("BTCUSDC", "USDC", "USDC", "BTC"),
        ("GAPUSDT", "USDT", "USDT", "GAP"),
    ]
    classifications = [
        {
            "symbol": symbol,
            "membership_class": "confirmed_perpetual",
            "accepted": True,
            "blocking": False,
            "in_archive": True,
            "in_current_exchange": True,
            "name_pattern_hint": "",
            "evidence": [
                {
                    "kind": "exchange_info",
                    "endpoint": "/fapi/v1/exchangeInfo",
                    "symbol": symbol,
                    "pair": symbol,
                    "contract_type": "PERPETUAL",
                    "status": "TRADING",
                    "underlying_type": "COIN",
                    "base_asset": base,
                    "quote_asset": quote,
                    "margin_asset": margin,
                    "onboard_ms": _ONBOARD_MS,
                    "delivery_ms": None,
                    "closed_observed_ms": None,
                    "semantics_state": "proved",
                }
            ],
        }
        for symbol, margin, quote, base in accepted_membership
    ] + [
        {
            "symbol": f"REJECT{index}USDT",
            "membership_class": "unresolved_name",
            "accepted": False,
            "blocking": True,
            "in_archive": True,
            "in_current_exchange": False,
            "name_pattern_hint": "",
            "evidence": [],
        }
        for index in range(2)
    ]
    matrix_rows = [
        {
            "product": product,
            "universe_coverage_gaps": [
                {
                    "symbol": f"GAP{index}USDT",
                    "family_group": "klines",
                    "families": [family],
                    "status": "interior_month_gap",
                    "kind": "interior_month_gap",
                    "blocking": True,
                    "first_observed": "2020-01",
                    "last_observed": "2020-03",
                    "missing_month_count": 1,
                    "explained_by": "",
                }
                for index, family in enumerate(families)
            ],
            "typed_gap_symbols": [f"TYPED{index}USDT" for index in range(index_count)],
        }
        for product, families, index_count in (
            ("binance_usdm_bar_1h", ("daily/klines", "monthly/klines"), 2),
            ("binance_usdm_open_interest_5m", ("daily/metrics",), 1),
            ("binance_usdm_cost_calibration", ("daily/bookTicker",), 1),
        )
    ]
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
        # Official contract metadata maps a Binance-native identity to a snapshot
        # digest, exactly as the pinned file does.
        "symbol_snapshot": {
            native: _sha256(native.encode("utf-8")) for native in supported_natives
        },
    }
    report = {
        "generated_at": _CUTOFF,
        "plan_lock": {"plan_version": 4, "plan_digest": "9" * 64, "inputs": inputs},
        # The accepted report's own sample records: the lineage authority for
        # availability semantics and retrieval time.
        "samples": sample_records,
        # The accepted product matrix, with its own product-scoped coverage gaps and
        # typed-gap memberships. Coverage is never inferred from Coinalyze alone.
        "product_matrix": matrix_rows,
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
        # A real accepted/rejected split with real contract evidence, including a
        # non-USDT margin example. Rejected rows are exclusion evidence only.
        "membership": {"classifications": classifications},
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
        # ADR-0025 section 4: this fixture's own logical/physical/alias decomposition.
        "ACCEPTED_LOGICAL_SAMPLE_RECORDS": len(sample_records),
        "ACCEPTED_PHYSICAL_SAMPLE_BINDINGS": len(
            {str(item["key"]) for item in sample_records}
        ),
        "ACCEPTED_FOLDED_SAMPLE_ALIASES": len(alias_keys),
        # ADR-0025 section 6 and ADR-0026 section 5: this fixture's coverage authority.
        "ACCEPTED_SOURCE_COVERAGE_GAPS": sum(
            len(row["universe_coverage_gaps"]) for row in matrix_rows
        ),
        "ACCEPTED_TYPED_GAP_MEMBERSHIPS": sum(
            len(row["typed_gap_symbols"]) for row in matrix_rows
        ),
        "ACCEPTED_MEMBERSHIP_CLASSIFICATIONS": len(classifications),
        "ACCEPTED_MEMBERSHIP_IDENTITIES": len(accepted_membership),
        "ACCEPTED_DETAILED_MEMBERSHIP_IDENTITIES": len(accepted_membership),
        "ACCEPTED_FUNDING_ONLY_MEMBERSHIP_IDENTITIES": 0,
        "ACCEPTED_REJECTED_MEMBERSHIP_ROWS": (
            len(classifications) - len(accepted_membership)
        ),
        "ACCEPTED_FEE_AUTHORITY_GAPS": len(accepted_membership),
        "ACCEPTED_KNOWN_COVERAGE_ROWS": (
            sum(len(row["universe_coverage_gaps"]) for row in matrix_rows)
            + len(accepted_membership)
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
        "sample_records": sample_records,
        "alias_keys": alias_keys,
        "matrix_rows": matrix_rows,
        "classifications": classifications,
        "accepted_membership": accepted_membership,
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
    assert credit["key_set_sha256"] == sizing.requirement_key_set_sha256(
        credit["keys"]
    )
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
    receipt_path = tmp_path / "231_receipt.json"
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
    receipt_path = tmp_path / "231_receipt.json"
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
def test_every_family_measures_typed_payload_and_overhead(
    tmp_path: Path, family: str
) -> None:
    """Each required product is measured with payload separated from file overhead."""
    body = _csv(family, 7)
    payload = _zip("data.csv", body)
    outputs = contributions_for_family(family)
    assert len(outputs) == sizing.OUTPUT_MULTIPLICITY[family]
    for index, output in enumerate(outputs):
        measurement = measure_typed_envelope(
            _cohort_sample(family),
            payload=payload,
            output=output,
            destination=tmp_path / f"{family.replace('/', '_')}-{index}.parquet",
            schema_kind="headerless",
        )
        assert measurement.rows == 7
        assert measurement.source_rows == 7
        # The exact ZIP member size, not a reconstruction from parsed tokens.
        assert measurement.extracted_member_bytes == len(body)
        assert measurement.compressed_archive_bytes == len(payload)
        # Payload, footer, framing, and residue account for every file byte exactly.
        assert (
            measurement.payload_bytes
            + measurement.footer_bytes
            + measurement.framing_bytes
            + measurement.residual_bytes
            == measurement.file_bytes
        )
        assert measurement.payload_bytes > 0
        assert measurement.framing_bytes == 8 + 4
        assert measurement.row_groups >= 1
        assert measurement.pyarrow_version
        # Every column is fixed-width typed or dictionary encoded; nothing is a raw
        # per-row string copy of the source token.
        schema = output.schema()
        assert not any(field.type == pa.string() for field in schema)


def test_the_required_product_contract_is_complete_and_named_by_the_ticket() -> None:
    contract = prove_product_contract()
    # The ticket's product names are contract; no packaging name may appear here.
    assert contract["required_products"] == list(REQUIRED_PRODUCTS)
    assert set(REQUIRED_PRODUCTS) == {
        "binance_usdm_perpetual_membership",
        "binance_usdm_bar_1h",
        "binance_usdm_trade_flow_1h",
        "binance_usdm_open_interest_5m",
        "binance_usdm_funding_realized",
        "binance_usdm_funding_indicative_1h",
        "binance_usdm_mark_index_basis_1h",
        "binance_usdm_liquidation_observed_daily",
        "binance_usdm_cost_calibration",
        "binance_usdm_coverage_gap",
        "binance_usdm_harmonic_bundle",
    }
    for family in PHYSICAL_FAMILIES:
        # The declared fields of a family are its known schema's field names. The
        # fixture token tuples are row *values* and are never field names.
        declared = set(KNOWN_ARCHIVE_SCHEMAS[_hint(family)]["headerless"])
        reached: set[str] = set()
        for item in contributions_for_family(family):
            reached |= set(item.source_fields())
        # No declared field of any family is dropped, including both cost products.
        assert declared <= reached
    # Daily and monthly packaging of one product feeds one product, not two products.
    bar = contributions_for_product("binance_usdm_bar_1h")
    assert {item.family for item in bar} == {"daily/klines", "monthly/klines"}
    assert {item.product for item in bar} == {"binance_usdm_bar_1h"}
    assert {item.component for item in bar} == {"daily_klines", "monthly_klines"}
    # Premium index klines contribute to indicative funding and to basis, never to a
    # taker-flow product.
    premium_contributions = list(contributions_for_family("daily/premiumIndexKlines"))
    premium = [item.product for item in premium_contributions]
    assert set(premium) == {
        "binance_usdm_funding_indicative_1h",
        "binance_usdm_mark_index_basis_1h",
    }
    # Scoped to the premium-index set just built. The whole contribution table
    # necessarily contains the required trade-flow product, so asserting over it
    # would test the opposite of the intended statement.
    assert not any("taker_flow" in item.name for item in premium_contributions)
    # Trade flow keeps the totals as well as the taker-buy side.
    flow_fields = {
        column.source_field
        for item in contributions_for_product("binance_usdm_trade_flow_1h")
        for column in item.columns
    }
    assert {"volume", "quote_volume", "taker_buy_volume", "taker_buy_quote_volume"} <= (
        flow_fields
    )
    # The cost product keeps every field of every row.
    ticker = contribution("binance_usdm_cost_calibration:daily_book_ticker")
    assert set(ticker.source_fields()) == set(
        KNOWN_ARCHIVE_SCHEMAS["bookTicker"]["headerless"]
    )
    depth = contribution("binance_usdm_cost_calibration:daily_book_depth")
    assert set(depth.source_fields()) == set(
        KNOWN_ARCHIVE_SCHEMAS["bookDepth"]["headerless"]
    )
    # Compact lineage: a partition-local reference, never a repeated source key string.
    assert [column.name for column in ticker.columns][:3] == [
        "raw_object_ref", "source_row_ordinal", "venue_symbol"
    ]
    assert "source_key" not in {column.name for column in ticker.columns}


def test_every_required_product_has_an_explicit_schema_and_bound() -> None:
    contract = prove_product_contract()
    fixed = contract["non_archive_product_schemas"]
    for product in (
        "binance_usdm_perpetual_membership",
        "binance_usdm_coverage_gap",
        "binance_usdm_liquidation_observed_daily",
        "binance_usdm_harmonic_bundle",
    ):
        assert product in fixed
        assert fixed[product]
    archive_products = {item.product for item in sizing.PRODUCT_CONTRIBUTIONS}
    assert archive_products | set(fixed) == set(REQUIRED_PRODUCTS)
    assert set(contract["cost_component_schemas"]) == set(sizing.COST_COMPONENTS)
    # The observed-liquidation product is typed, not a JSON point string.
    liquidation = {field["name"]: field for field in fixed[
        "binance_usdm_liquidation_observed_daily"
    ]}
    assert "point_token" not in liquidation
    assert liquidation["event_time_ms"]["arrow_type"] == "int64"
    for name in ("long_liquidation", "short_liquidation"):
        assert liquidation[name]["arrow_type"] == "decimal128(38, 18)"
    assert liquidation["native_symbol"]["arrow_type"].startswith("dictionary")
    assert liquidation["provider_symbol"]["arrow_type"].startswith("dictionary")
    # The pinned exact decimal policy, and no float anywhere in it.
    policy = contract["decimal_policy"]
    assert policy["arrow_type"] == "decimal128(38, 18)"
    assert policy["precision"] == 38 and policy["scale"] == 18
    # Every fixed cadence is declared; the two cost families are named event-driven.
    cadence = contract["cadence"]
    assert cadence["fixed_seconds"]["daily/metrics"] == 300
    assert cadence["fixed_seconds"]["daily/klines"] == 3_600
    # ADR-0025 section 7: one hour, never eight, until a stricter bound is proved.
    assert cadence["fixed_seconds"]["monthly/fundingRate"] == 3_600
    assert sorted(cadence["event_driven_families"]) == sorted(COST_FAMILIES)
    assert set(cadence["fixed_seconds"]) | set(cadence["event_driven_families"]) == set(
        PHYSICAL_FAMILIES
    )


def test_no_typed_column_uses_a_binary_float() -> None:
    for item in sizing.PRODUCT_CONTRIBUTIONS:
        for field in item.schema():
            assert field.type not in {pa.float32(), pa.float64()}
    for product in sizing.NON_ARCHIVE_PRODUCTS:
        schema = sizing.final_product_schema(product)
        for field in schema:
            assert field.type not in {pa.float32(), pa.float64()}
    source = Path(sizing.__file__).read_text(encoding="utf-8")
    assert "pa.float64()" not in source
    assert "float(" not in source


def test_headed_input_is_measured_as_headed(tmp_path: Path) -> None:
    output = contributions_for_family("daily/klines")[0]
    payload = _zip("data.csv", _csv("daily/klines", 5, headed=True))
    measurement = measure_typed_envelope(
        _cohort_sample(),
        payload=payload,
        output=output,
        destination=tmp_path / "a.parquet",
        schema_kind="headed",
    )
    assert measurement.schema_kind == "headed"
    assert measurement.rows == 5
    # A headed file whose checkpoint claims headerless is a disagreement, not a guess.
    with pytest.raises(SizingError, match="header form disagrees"):
        measure_typed_envelope(
            _cohort_sample(),
            payload=payload,
            output=output,
            destination=tmp_path / "b.parquet",
            schema_kind="headerless",
        )
    headerless = _zip("data.csv", _csv("daily/klines", 5))
    with pytest.raises(SizingError, match="header form disagrees"):
        measure_typed_envelope(
            _cohort_sample(),
            payload=headerless,
            output=output,
            destination=tmp_path / "c.parquet",
            schema_kind="headed",
        )


def test_row_grouping_and_determinism(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = contributions_for_family("daily/bookTicker")[0]
    payload = _zip("data.csv", _csv("daily/bookTicker", 10))
    monkeypatch.setattr(sizing, "SIZING_ROW_BATCH", 4)
    batched = measure_typed_envelope(
        _cohort_sample("daily/bookTicker"),
        payload=payload,
        output=output,
        destination=tmp_path / "a.parquet",
        schema_kind="headerless",
    )
    assert batched.row_groups == 3
    # Row-group metadata is charged per row group, never once for a whole family.
    assert batched.footer_per_row_group() >= 1
    monkeypatch.undo()
    first = measure_typed_envelope(
        _cohort_sample("daily/bookTicker"),
        payload=payload,
        output=output,
        destination=tmp_path / "b.parquet",
        schema_kind="headerless",
    )
    second = measure_typed_envelope(
        _cohort_sample("daily/bookTicker"),
        payload=payload,
        output=output,
        destination=tmp_path / "c.parquet",
        schema_kind="headerless",
    )
    assert first.parquet_sha256 == second.parquet_sha256
    assert first.row_groups == 1


def test_typed_products_never_repeat_identity_metadata_per_row(
    tmp_path: Path,
) -> None:
    """The superseded surrogate stored family, symbol, interval, and key on every row."""
    payload = _zip("data.csv", _csv("daily/bookTicker", 2_000))
    output = contributions_for_family("daily/bookTicker")[0]
    typed = measure_typed_envelope(
        _cohort_sample("daily/bookTicker"),
        payload=payload,
        output=output,
        destination=tmp_path / "typed.parquet",
        schema_kind="headerless",
    )
    assert typed.rows == 2_000
    names = set(output.schema().names)
    for repeated in ("physical_family", "economic_interval", "source_key"):
        assert repeated not in names
    # Identity survives as one compact partition-local reference plus one dictionary.
    assert "raw_object_ref" in names
    assert output.schema().field("raw_object_ref").type == pa.int32()
    assert output.schema().field("venue_symbol").type == pa.dictionary(
        pa.int32(), pa.string()
    )
    # No target column stores a source token as a per-row string.
    assert all(field.type != pa.string() for field in output.schema())


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
        measure_typed_envelope(
            _cohort_sample(),
            payload=payload,
            output=contributions_for_family("daily/klines")[0],
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


def _typed_measurement(
    output_name: str,
    *,
    payload_bytes: int = 3,
    compressed: int = 2,
    rows: int = 1,
    row_groups: int = 1,
    footer: int = 1,
) -> Any:
    """One synthetic typed measurement with exact, separately named components."""
    item = contribution(output_name)
    return sizing.TypedEnvelopeMeasurement(
        key=f"k-{output_name}",
        family=item.family,
        contribution=output_name,
        product=item.product,
        symbol="BTCUSDT",
        economic_interval="2020-01-01",
        schema_kind="headerless",
        compressed_archive_bytes=compressed,
        extracted_member_bytes=4,
        source_rows=rows,
        rows=rows,
        row_groups=row_groups,
        payload_bytes=payload_bytes,
        footer_bytes=footer,
        framing_bytes=12,
        residual_bytes=0,
        file_bytes=payload_bytes + footer + 12,
        parquet_sha256="0" * 64,
        writer_identity="w",
        pyarrow_version="x",
    )


def _lineage_model(
    payload: int = 0, footer: int = 0, framing: int = 0
) -> Any:
    """A lineage charge whose three parts are set explicitly by each test."""
    return sizing.LineageManifestModel(
        payload_bytes_per_mapping=payload,
        footer_per_row_group_bytes=footer,
        framing_bytes=framing,
        witness_partitions=(
            {
                "required_product": "binance_usdm_bar_1h",
                "native_symbol": "BTCUSDT",
                "utc_month": "2020-01",
                "mappings": 1,
                "file_bytes": payload + footer + framing,
            },
        ),
    )


def _all_measurements(**overrides: Any) -> list[Any]:
    """One synthetic measurement per declared product contribution."""
    return [
        overrides.get(item.name) or _typed_measurement(item.name)
        for item in sizing.PRODUCT_CONTRIBUTIONS
    ]


def _one_object_per_family(byte_size: int = 500) -> list[PhysicalObject]:
    return [
        PhysicalObject(
            key=_key(family, "BTCUSDT", "2020-01-01"),
            family=family,
            symbol="BTCUSDT",
            economic_interval="2020-01-01",
            byte_size=byte_size,
        )
        for family in PHYSICAL_FAMILIES
    ]


def test_partitions_group_by_required_product_symbol_and_month() -> None:
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
            key=_key("monthly/klines", "BTCUSDT", "2020-01"),
            family="monthly/klines",
            symbol="BTCUSDT",
            economic_interval="2020-01",
            byte_size=500,
        )
    ]
    groups = group_objects(objects)
    # Daily and monthly packaging of one product land in the same product partition.
    assert set(groups) == {
        ("binance_usdm_bar_1h", "BTCUSDT", "2020-01"),
        ("binance_usdm_trade_flow_1h", "BTCUSDT", "2020-01"),
    }
    assert len(groups[("binance_usdm_bar_1h", "BTCUSDT", "2020-01")]) == 4
    projections = project_typed_partitions(
        measurements=_all_measurements(),
        objects=objects
        + [
            item
            for item in _one_object_per_family(10)
            if item.family not in {"daily/klines", "monthly/klines"}
        ],
        lineage=_lineage_model(),
    )
    bar = next(item for item in projections if item.product == "binance_usdm_bar_1h")
    # One partition holding both packagings, and the payload of each component is
    # ceilinged separately before they are summed.
    assert bar.partition_count == 1
    assert bar.projected_payload_bytes == ceil_div(300 * 3, 2) + ceil_div(500 * 3, 2)
    assert bar.projected_overhead_bytes == 1 * 1 + 12
    assert bar.projected_bytes == bar.projected_payload_bytes + bar.projected_overhead_bytes
    assert bar.largest_partition_bytes == bar.projected_bytes
    assert {item["physical_family"] for item in bar.components} == {
        "daily/klines",
        "monthly/klines",
    }


def test_partition_manifest_mappings_are_counted_per_product_partition() -> None:
    objects = _one_object_per_family()
    projections = project_typed_partitions(
        measurements=_all_measurements(),
        objects=objects,
        lineage=_lineage_model(payload=7),
    )
    # A kline object feeds two required products, so it is mapped in both partitions.
    # The complete one-object-per-family fixture carries both a daily and a monthly
    # kline object, so each kline-fed product maps two raw objects, not one.
    bar = next(item for item in projections if item.product == "binance_usdm_bar_1h")
    flow = next(
        item for item in projections if item.product == "binance_usdm_trade_flow_1h"
    )
    assert bar.manifest_mappings == 2
    assert flow.manifest_mappings == 2
    assert bar.projected_manifest_bytes == 14
    assert flow.projected_manifest_bytes == 14
    # Mark/index basis is fed by mark, index, and premium klines in both daily and
    # monthly packaging, so its one partition maps six raw objects.
    basis = next(
        item for item in projections if item.product == "binance_usdm_mark_index_basis_1h"
    )
    assert basis.manifest_mappings == 6
    assert basis.projected_manifest_bytes == 42
    # Mark, index, and premium contribute bytes independently but publish one aligned
    # target grid. The monthly 744-hour ceiling wins; the input components do not sum.
    assert basis.partition_rows == (744,)
    assert basis.projected_rows == 744
    assert sizing.quality_gap_reservation(basis.partition_rows[0]) == 372
    # The same aligned-grid rule applies to every multi-input target product. Daily and
    # monthly kline packaging feed one bar grid rather than two additive row streams.
    assert bar.partition_rows == (744,)
    assert bar.projected_rows == 744
    total_mappings = sum(item.manifest_mappings for item in projections)
    # Cross-product references are counted in every product they feed, never once.
    assert total_mappings == sum(
        len(contributions_for_family(item.family)) for item in objects
    )
    assert total_mappings > len(objects)


def test_a_tiny_file_footer_is_not_amplified_across_a_product() -> None:
    """ADR-0024: a one-row archive charges its own overhead to its own partition."""
    tiny = _typed_measurement(
        "binance_usdm_cost_calibration:daily_book_depth",
        payload_bytes=1,
        compressed=1,
        rows=1,
        footer=900,
    )
    objects = _one_object_per_family(1_000_000)
    projections = project_typed_partitions(
        measurements=_all_measurements(
            **{"binance_usdm_cost_calibration:daily_book_depth": tiny}
        ),
        objects=objects,
        lineage=_lineage_model(),
    )
    cost = next(
        item
        for item in projections
        if item.product == "binance_usdm_cost_calibration"
        and item.component == "retained_book_depth"
    )
    # One partition, so the 900-byte footer bound is charged once, not against every
    # projected byte of the product.
    assert cost.partition_count == 1
    assert cost.projected_overhead_bytes == cost.projected_row_groups * 900 + 12
    assert cost.projected_overhead_bytes < cost.projected_payload_bytes
    # The superseded whole-file ratio would have multiplied 902/1 across every byte.
    assert cost.projected_bytes < 1_000_000 * 902


def test_daily_metrics_uses_its_fixed_five_minute_calendar_ceiling() -> None:
    """The metrics archive key carries no interval segment; the cadence is pinned."""
    key = _key("daily/metrics", "BTCUSDT", "2020-01-01")
    assert "/5m/" not in key and "/1h/" not in key
    assert sizing.family_cadence_seconds("daily/metrics") == 300
    member = PhysicalObject(
        key=key,
        family="daily/metrics",
        symbol="BTCUSDT",
        economic_interval="2020-01-01",
        byte_size=1,
    )
    # 86,400 seconds at 300 seconds each is 288 rows for one whole day.
    assert sizing.calendar_row_bound([member]) == 288
    assert sizing.calendar_row_bound([member, member]) == 576
    # An event-driven cost family has no calendar ceiling at all.
    cost = PhysicalObject(
        key=_key("daily/bookTicker", "BTCUSDT", "2020-01-01"),
        family="daily/bookTicker",
        symbol="BTCUSDT",
        economic_interval="2020-01-01",
        byte_size=1,
    )
    assert sizing.family_cadence_seconds("daily/bookTicker") == 0
    assert sizing.calendar_row_bound([cost]) == 0
    # An undeclared family blocks; it never silently becomes event-driven.
    with pytest.raises(SizingError, match="no accepted cadence declaration"):
        sizing.family_cadence_seconds("daily/unknownFamily")


def test_the_greater_applicable_row_bound_wins_per_component() -> None:
    # A tiny observed ratio must not defeat the pinned five-minute metrics ceiling.
    weak = _typed_measurement(
        "binance_usdm_open_interest_5m:daily_metrics",
        payload_bytes=1,
        compressed=1_000,
        rows=1,
    )
    objects = _one_object_per_family(1_000)
    projections = project_typed_partitions(
        measurements=_all_measurements(
            **{"binance_usdm_open_interest_5m:daily_metrics": weak}
        ),
        objects=objects,
        lineage=_lineage_model(),
    )
    metrics = next(
        item for item in projections if item.product == "binance_usdm_open_interest_5m"
    )
    # The observed ratio would have projected one row; the calendar ceiling is 288.
    assert metrics.projected_rows == 288
    component = metrics.components[0]
    assert component["cadence_seconds"] == 300
    assert component["row_bound_source"] == "declared cadence calendar maximum"
    # An event-driven product keeps the observed exact ratio as its ceiling.
    cost = next(
        item for item in projections if item.product == "binance_usdm_cost_calibration"
    )
    assert all(
        item["row_bound_source"] == "greatest observed exact row-to-compressed ratio"
        for item in cost.components
    )


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
    # A supported mapping without a retained contract snapshot blocks; it never gets
    # zero days and never invents a bound.
    with pytest.raises(SizingError, match="no retained contract snapshot"):
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
        lineage=_lineage_model(),
        staging=tmp_path,
    )
    # Envelopes are measured under native identity and name their provider identity.
    for envelope in projection.envelopes:
        assert envelope["provider_symbol"] == accepted["provider_of"][
            envelope["native_symbol"]
        ]
    assert sorted(item["native_symbol"] for item in projection.envelopes) == sorted(
        accepted["anchor_natives"]
    )
    # The normalized ratio is a Coinalyze envelope ratio, never a Binance family ratio.
    assert projection.envelope_numerator > 0 and projection.envelope_denominator > 0
    assert projection.envelopes
    footer = max(item["footer_per_row_group_bytes"] for item in projection.envelopes)
    framing = max(item["framing_bytes"] for item in projection.envelopes)
    assert projection.projected_normalized_bytes == sum(
        ceil_div(points * projection.envelope_numerator, projection.envelope_denominator)
        + max(1, ceil_div(points, sizing.SIZING_ROW_BATCH)) * footer
        + framing
        for points in _expected_group_bytes(projection, supported, lifecycles)
    )
    assert projection.partition_count == len(
        _expected_group_bytes(projection, supported, lifecycles)
    )
    assert projection.largest_partition_bytes > 0
    rendered = json.dumps(projection.to_dict())
    assert "apiKey" not in rendered and "api_key" not in rendered


def _expected_group_bytes(_projection: Any, supported: Any, lifecycles: Any) -> list[int]:
    groups: dict[tuple[str, str], int] = {}
    for symbol in supported:
        first, last = lifecycles[symbol]
        for day in range(first, last + 1):
            month = datetime.fromordinal(day).strftime("%Y-%m")
            groups[(symbol, month)] = groups.get((symbol, month), 0) + 1
    return list(groups.values())


def test_retained_liquidation_points_are_typed_and_exact(tmp_path: Path) -> None:
    """The retained t/l/s lexemes become typed columns, never a stored JSON string."""
    body = json.dumps(
        [
            {
                "symbol": "BTCUSDT_PERP.A",
                "history": [
                    {"t": 1577836800, "l": "1.500000000000000001", "s": "2.5"},
                    {"t": 1577923200, "l": "0.1", "s": "0"},
                ],
            }
        ]
    ).encode("utf-8")
    measured = measure_liquidation_response(body, endpoint="/liquidation-history")
    provider, points = measured["series"][0]
    assert provider == "BTCUSDT_PERP.A"
    # Exact decimals, straight from the retained lexemes.
    assert points[0]["long_liquidation"] == Decimal("1.500000000000000001")
    assert points[0]["short_liquidation"] == Decimal("2.5")
    assert points[1]["long_liquidation"] == Decimal("0.1")
    assert points[0]["event_time_ms"] == 1577836800 * 1000
    assert all(isinstance(item["long_liquidation"], Decimal) for item in points)
    envelope = write_liquidation_envelope(
        symbol="BTCUSDT",
        provider_symbol=provider,
        endpoint="/liquidation-history",
        points=points,
        destination=tmp_path / "liq.parquet",
    )
    # The envelope records the venue's native identity and the provider's separately.
    assert envelope["required_product"] == "binance_usdm_liquidation_observed_daily"
    assert envelope["native_symbol"] == "BTCUSDT"
    assert envelope["provider_symbol"] == "BTCUSDT_PERP.A"
    assert envelope["points"] == 2
    # Payload and file overhead are separated exactly, as for every other product.
    assert (
        envelope["payload_bytes"]
        + envelope["footer_bytes"]
        + envelope["framing_bytes"]
        + envelope["residual_bytes"]
        == envelope["file_bytes"]
    )
    assert envelope["bytes_per_point"] > 0
    names = {field["name"] for field in envelope["schema"]}
    assert "point_token" not in names
    assert {"event_time_ms", "long_liquidation", "short_liquidation"} <= names
    huge = 2**53
    # The same exact comparison the projection uses, past float64 resolution.
    assert ratio_exceeds((envelope["file_bytes"] * huge + 1, huge), (
        envelope["file_bytes"], 1
    ))


def test_a_non_numeric_retained_liquidation_lexeme_blocks() -> None:
    body = json.dumps(
        [{"symbol": "BTCUSDT_PERP.A", "history": [{"t": 1577836800, "l": "x", "s": "1"}]}]
    ).encode("utf-8")
    with pytest.raises(SizingError, match="not a decimal lexeme"):
        measure_liquidation_response(body, endpoint="/liquidation-history")
    absent = json.dumps(
        [{"symbol": "BTCUSDT_PERP.A", "history": [{"t": 1577836800, "s": "1"}]}]
    ).encode("utf-8")
    with pytest.raises(SizingError, match="not an exact numeric lexeme"):
        measure_liquidation_response(absent, endpoint="/liquidation-history")


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
    target = tmp_path / "231_receipt.json"
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
        "receipt_path": tmp_path / "231_receipt.json",
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
    target = tmp_path / "231_receipt.json"
    # The returned mapping and the durable bytes are the same document - not two
    # structures that merely serialize to equal bytes.
    assert target.read_bytes() == sizing.canonical_json(receipt)
    assert receipt == json.loads(target.read_text())
    assert identity["receipt_sha256"] == _sha256(target.read_bytes())
    assert identity["receipt_bytes"] == len(target.read_bytes())
    assert receipt["filesystem"]["durable_receipt_bytes"] == len(target.read_bytes())
    assert "receipt_sha256" not in receipt
    for section in (
        "authority",
        "physical_inputs",
        "cohort",
        "typed_schema_contract",
        "lineage",
        "coverage_authority",
        "fee_authority",
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
    assert receipt["schema_version"] == "cex002_gate2_storage_sizing_v2"
    assert receipt["storage_preflight_state"] in {STATE_SUFFICIENT, STATE_BLOCKED}
    assert receipt["code_identity"]["sizing_source_sha256"]
    assert receipt["physical_inputs"]["combined_objects"] == sizing.ACCEPTED_COMBINED_OBJECTS
    assert (
        receipt["physical_inputs"]["projected_new_binance_raw_bytes"]
        == sizing.ACCEPTED_NEW_BINANCE_RAW_BYTES
    )
    capacity = receipt["capacity"]
    # ADR-0024 section 5: six components, counted once, without overlap.
    components = (
        "new_binance_raw_bytes",
        "new_coinalyze_raw_bytes",
        "typed_normalized_partition_bytes",
        "catalog_manifest_bundle_bytes",
        "bounded_temporary_work_bytes",
        "operating_reserve_bytes",
    )
    # Exactly six components exist; the block carries nothing else that is a byte count.
    assert set(capacity) == set(components) | {
        "total_future_storage_bytes",
        "reserve_rule",
        "equation",
    }
    for name in components:
        value = capacity[name]
        assert isinstance(value, int) and not isinstance(value, bool) and value >= 0
    assert capacity["total_future_storage_bytes"] == sum(
        capacity[name] for name in components
    )
    # No component is counted twice: removing the five non-reserve terms from the exact
    # total leaves exactly the reserve.
    assert capacity["total_future_storage_bytes"] - sum(
        capacity[name] for name in components if name != "operating_reserve_bytes"
    ) == capacity["operating_reserve_bytes"]
    assert capacity["operating_reserve_bytes"] >= MINIMUM_OPERATING_RESERVE_BYTES
    # The normalized output is allocated exactly once: the bounded temporary work unit
    # is a single greatest explicit unit, never a second complete normalized tree.
    projections = receipt["projections"]
    assert (
        capacity["typed_normalized_partition_bytes"]
        == projections["typed_normalized_bytes"]
    )
    # The observed-liquidation product is typed; no JSON point string is stored.
    assert "point_token" not in sizing.canonical_json(receipt).decode()
    explicit_work_units = {
        sizing.ACCEPTED_LARGEST_SELECTED_OBJECT_BYTES,
        receipt["partitioning"]["largest_projected_partition_bytes"],
        receipt["partitioning"]["bundle_transaction_bytes"],
    }
    assert capacity["bounded_temporary_work_bytes"] == max(explicit_work_units)
    # ADR-0024 section 5 bounds temporary work by the greatest single explicit unit, so
    # it is one of those units and never an accumulation of them. It is deliberately not
    # required to be smaller than final normalized-plus-catalog storage: a large accepted
    # compressed object legitimately exceeds a small projected normalized universe.
    if len(explicit_work_units) > 1:
        assert capacity["bounded_temporary_work_bytes"] < sum(explicit_work_units)
    # The catalog/manifest/bundle term is the measured one, included exactly once.
    assert (
        capacity["catalog_manifest_bundle_bytes"]
        == receipt["partitioning"]["catalog_overhead_bytes"]
    )
    # Payload and file overhead are projected separately, never one whole-file ratio.
    assert (
        projections["typed_payload_bytes"]
        + projections["typed_overhead_bytes"]
        + projections["typed_partition_manifest_bytes"]
        == projections["typed_normalized_bytes"]
    )
    assert projections["projected_row_groups"] > 0
    future = receipt["future_width_allocations"]
    assert set(future) == {
        "reference_identity",
        "membership_terms",
        "bundle_partition_fields",
        "quality_gap_bounds",
        "lineage_receipt_fields",
        "projected_source_receipts",
    }
    assert projections["future_field_payload_bytes"] == sum(
        future[name]["bytes"]
        for name in (
            "reference_identity",
            "membership_terms",
            "bundle_partition_fields",
            "quality_gap_bounds",
            "lineage_receipt_fields",
        )
    )
    assert future["projected_source_receipts"]["receipts"] == receipt["counts"][
        "projected_acquisition_receipts"
    ]
    assert receipt["partitioning"]["largest_projected_partition_bytes"] == (
        receipt["partitioning"]["largest_current_typed_partition_bytes"]
        + receipt["partitioning"]["largest_future_width_charge_bytes"]
    )
    assert receipt["partitioning"]["largest_future_width_charge_bytes"] > 0
    archive_products = {item.product for item in sizing.PRODUCT_CONTRIBUTIONS}
    assert {
        item["required_product"] for item in projections["required_products"]
    } == archive_products
    # Version-1 evidence is named as immutable and is never a version-2 target.
    immutable = receipt["partitioning"]["immutable_v1_evidence"]
    assert immutable["receipt_sha256"] == sizing.V1_ACCEPTED_RECEIPT_SHA256
    assert immutable["evidence_root"] == "evidence/sizing/v1/envelopes/sha256"
    assert sizing.SIZING_EVIDENCE_ROOT == "evidence/sizing/v2/envelopes/sha256"
    assert sizing.SIZING_RECEIPT_RELATIVE_PATH == (
        "research/sprint_004/231_CEX002_GATE2_STORAGE_SIZING_V2.json"
    )
    filesystem = receipt["filesystem"]
    assert filesystem["durable_receipt_bytes"] > 0
    assert filesystem["retained_sizing_evidence_bytes"] > 0
    counts = receipt["counts"]
    coverage = receipt["coverage_authority"]
    lineage = receipt["lineage"]
    retained_credit = receipt["physical_inputs"]["retained_credit"]
    assert lineage["retained_archive_requirement_keys"] == retained_credit[
        "valid_requirement_keys"
    ]
    assert lineage["retained_archive_key_set_sha256"] == retained_credit[
        "key_set_sha256"
    ]
    assert lineage["projected_unacquired_archive_requirement_keys"] == (
        receipt["physical_inputs"]["combined_objects"]
        - retained_credit["valid_requirement_keys"]
    )
    assert lineage["coefficient_only_keys_marked_retained"] == 0
    assert counts["count_sources"]["typed_gap_rows"].startswith("report coinalyze")
    assert receipt["partitioning"]["catalog_overhead_bytes"] == (
        sum(counts["catalog_page_components"].values()) * CATALOG_PAGE_BYTES
        + sizing.ACCEPTED_REPORT_BYTES
        + sizing.ACCEPTED_MANIFEST_DETAIL_BYTES
        + receipt["future_width_allocations"]["projected_source_receipts"]["bytes"]
    )
    # Lineage is charged once per raw object per product partition, inside the product
    # bytes, never once release-globally and never once per normalized row.
    manifest = projections["partition_lineage"]
    assert manifest["mappings"] == counts["partition_manifest_mappings"]
    assert counts["coverage_known_coverage_rows"] == coverage["known_coverage_rows"]
    assert counts["logical_sample_records"] == lineage["logical_records"]
    assert counts["physical_sample_bindings"] == lineage["physical_bindings"]
    assert counts["folded_sample_aliases"] == lineage["folded_aliases"]
    assert counts["coverage_rows_total"] == (
        coverage["known_coverage_rows"] + coverage["projected_quality_gap_rows"]
    )
    assert receipt["partitioning"]["partition_manifest_bytes"] == sum(
        item["projected_partition_manifest_bytes"]
        for item in projections["required_products"]
    ) + receipt["coinalyze"]["projected_partition_manifest_bytes"]
    assert counts["partition_manifest_projected_mappings"] >= counts[
        "physical_raw_objects"
    ]
    # The complete final target schema of every required product is published.
    schemas = projections["final_product_schemas"]
    assert set(schemas) == set(REQUIRED_PRODUCTS)
    assert all(schemas[product] for product in REQUIRED_PRODUCTS)
    # Target-only fields are measured from real derived values and charged once.
    targets = projections["target_only_fields"]
    assert targets["binance_usdm_trade_flow_1h"]["bytes_per_row"] > 0
    assert targets["binance_usdm_trade_flow_1h"]["measured_rows"] > 0
    assert projections["target_only_bytes"] == sum(
        item["projected_target_only_bytes"] for item in projections["required_products"]
    )
    assert projections["target_only_bytes"] > 0
    # Lineage: the accepted alias decomposition and the partition-local charge model.
    assert (
        lineage["logical_records"] - lineage["physical_bindings"]
        == lineage["folded_aliases"]
    )
    assert lineage["folded_aliases"] > 0
    assert lineage["retrieval_time_known_bindings"] > 0
    assert lineage["retrieval_time_unknown_bindings"] > 0
    model = projections["lineage_manifest_model"]
    assert model["payload_bytes_per_mapping"] > 0
    assert model["footer_per_row_group_bytes"] > 0
    assert model["framing_bytes_per_partition"] == 12
    bundle_projection = projections["fixed_schema_products"][
        "binance_usdm_harmonic_bundle"
    ]
    assert bundle_projection["projected_rows"] == (
        projections["partition_lineage"]["partitions"]
        + projections["partition_lineage"]["coinalyze_partitions"]
    )
    assert bundle_projection["projected_rows"] > counts["physical_sample_bindings"]
    intersection = receipt["partitioning"]["cross_product_partition_intersection"]
    assert receipt["partitioning"]["cross_product_intersection_sha256"] == _sha256(
        sizing.canonical_json(
            {"cross_product_partition_intersection": intersection}
        )
    )
    # Coverage: known source gaps, fee gaps, typed memberships, and quality reservation
    # are four separate published counts.
    coverage = receipt["coverage_authority"]
    assert coverage["known_coverage_rows"] == (
        coverage["accepted_source_coverage_gaps"] + coverage["fee_authority_gaps"]
    )
    assert coverage["accepted_typed_gap_memberships"] >= 0
    assert coverage["projected_quality_gap_rows"] > 0
    assert coverage["official_historical_fee_rows"] == 0
    assert coverage["source_gap_component"]["witness_measured_rows"] == coverage[
        "accepted_source_coverage_gaps"
    ]
    # Fee authority: zero history, two outcome-blind policy rows, no backdating.
    fee = receipt["fee_authority"]
    assert fee["official_historical_rows"] == 0
    assert fee["gap_kind"] == "historical_fee_schedule_unavailable"
    assert fee["policy_known_at"] == "2026-08-23T03:00:00Z"
    assert len(fee["scenario_policy_rows"]) == 2
    assert [row["maker_rate"] for row in fee["scenario_policy_rows"]] == [
        "0.000500000000000000",
        "0.001000000000000000",
    ]
    assert all(
        row["maker_credit_enabled"] is False for row in fee["scenario_policy_rows"]
    )
    # Every required product is named, with its own schema and byte bound.
    named = {item["required_product"] for item in projections["required_products"]}
    named |= set(projections["fixed_schema_products"]) & set(REQUIRED_PRODUCTS)
    named.add("binance_usdm_liquidation_observed_daily")
    assert named == set(REQUIRED_PRODUCTS)
    # ADR-0025/ADR-0026: a measurement dictionary key may name a component, but it
    # never creates a twelfth required product. The three fixed-schema cost components
    # name their parent product and their own component; every other block names itself.
    cost_component_keys = {
        "official_fee_schedule",
        "fee_authority_gap",
        "scenario_policy",
    }
    assert cost_component_keys <= set(sizing.COST_COMPONENTS)
    assert set(projections["fixed_schema_products"]) - cost_component_keys == {
        "binance_usdm_perpetual_membership",
        "binance_usdm_coverage_gap",
        "binance_usdm_harmonic_bundle",
        "typed_gap_membership",
        "quality_gap",
    }
    for product, block in projections["fixed_schema_products"].items():
        assert block["schema"]
        assert block["projected_bytes"] == (
            block["projected_payload_bytes"] + block["projected_overhead_bytes"]
        )
        if product in cost_component_keys:
            assert block["required_product"] == "binance_usdm_cost_calibration"
            assert block["component"] == product
        else:
            assert block["required_product"] == product
            assert "component" not in block
    # The five-component cost receipt carries the same parent/component identities.
    cost_blocks = receipt["cost_calibration_components"]
    for name in sizing.COST_COMPONENTS:
        block = cost_blocks[name]
        assert block["required_product"] == "binance_usdm_cost_calibration"
        assert block["component"] == name


@pytest.mark.parametrize(
    ("token", "message"),
    [
        ("", "has no value"),
        ("12.5", "not a strict integer"),
        ("1e3", "not a strict integer"),
        (" 12 ", ""),
        ("99999999999999999999999999", "overflows its declared width"),
    ],
)
def test_strict_integer_conversion(token: str, message: str) -> None:
    call = {"key": "k", "output": "o", "column": "c", "row": 3}
    if not message:
        assert sizing.convert_integer(token, **call) == 12
        return
    with pytest.raises(SizingError, match=message) as failure:
        sizing.convert_integer(token, **call)
    # Only structure reaches the failure surface: never the rejected source token.
    assert token.strip() not in str(failure.value) or not token.strip()
    assert failure.value.context["column"] == "c"
    assert failure.value.context["source_row_ordinal"] == 3


@pytest.mark.parametrize(
    ("token", "message"),
    [
        ("", "has no value"),
        ("nan", "not a decimal lexeme"),
        ("NaN", "not a decimal lexeme"),
        ("inf", "not a decimal lexeme"),
        ("-Infinity", "not a decimal lexeme"),
        ("1.2.3", "not a decimal lexeme"),
        ("abc", "not a decimal lexeme"),
        ("0x10", "not a decimal lexeme"),
        # More fractional digits than the pinned scale can hold exactly.
        ("0." + "1" * 19, "exceeds the pinned scale"),
        # More significant digits than the pinned precision can hold.
        ("1" * 21, "overflows the pinned precision"),
    ],
)
def test_exact_decimal_conversion_blocks_instead_of_rounding(
    token: str, message: str
) -> None:
    with pytest.raises(SizingError, match=message) as failure:
        sizing.convert_decimal(token, key="k", output="o", column="c", row=0)
    # Only structure reaches the failure surface: never the rejected source token.
    stripped = token.strip()
    assert not stripped or stripped not in str(failure.value)
    assert failure.value.context["column"] == "c"


@pytest.mark.parametrize(
    "token",
    [
        "0",
        "1.5",
        "-0.000000000000000001",
        "123456789012345678.999999999999999999",
        "0.1",
        "0.30000000000000004",
        "1e3",
        "-2.5E-3",
        "99999999999999999999.000000000000000001",
    ],
)
def test_adversarial_decimal_lexemes_survive_exactly(token: str) -> None:
    """Every accepted lexeme keeps its exact value; nothing goes through a float."""
    value = sizing.convert_decimal(token, key="k", output="o", column="c", row=0)
    assert isinstance(value, Decimal)
    assert value == Decimal(token)
    # A float round trip of these lexemes is not exact, which is precisely the defect
    # the decimal policy removes.
    assert value.as_tuple().exponent == -sizing.DECIMAL_SCALE
    assert Decimal(token) - value == 0


def test_a_float_round_trip_would_have_changed_the_value() -> None:
    token = "0.1"
    exact = sizing.convert_decimal(token, key="k", output="o", column="c", row=0)
    assert exact == Decimal("0.1")
    # The rejected float64 policy could not represent this lexeme exactly.
    assert Decimal(float(token)) != Decimal(token)


def test_strict_timestamp_and_dictionary_conversion() -> None:
    assert sizing.convert_timestamp_text(
        "2020-01-01 00:00:00", key="k", output="o", column="c", row=0
    ) == _ONBOARD_MS
    with pytest.raises(SizingError, match="not an ISO UTC instant"):
        sizing.convert_timestamp_text(
            "not-a-time", key="k", output="o", column="c", row=0
        )
    assert sizing.convert_dictionary(
        " BTCUSDT ", key="k", output="o", column="c", row=0
    ) == "BTCUSDT"
    with pytest.raises(SizingError, match="has no value"):
        sizing.convert_dictionary("   ", key="k", output="o", column="c", row=0)


def test_a_failed_conversion_blocks_the_whole_envelope(tmp_path: Path) -> None:
    """A failed row is never dropped, rounded, or replaced with zero."""
    body = b"1577836800000,1.0,2.0,0.5,not-a-number,10,1577840399999,15.0,7,4.0,6.0,0\n"
    payload = _zip("data.csv", body)
    destination = tmp_path / "typed.parquet"
    # The pinned converter contract, not the obsolete wording.
    with pytest.raises(SizingError, match="not a decimal lexeme") as failure:
        measure_typed_envelope(
            _cohort_sample(),
            payload=payload,
            output=contributions_for_family("daily/klines")[0],
            destination=destination,
            schema_kind="headerless",
        )
    assert failure.value.context["contribution"] == (
        "binance_usdm_bar_1h:daily_klines"
    )
    assert "not-a-number" not in str(failure.value)


def test_the_partition_manifest_maps_each_product_and_keeps_unknowns_unknown(
    tmp_path: Path,
) -> None:
    entries = [
        {
            "raw_object_ref": index // 2,
            "required_product": (
                "binance_usdm_bar_1h" if index % 2 == 0 else "binance_usdm_trade_flow_1h"
            ),
            "component": "daily_klines",
            "native_symbol": "BTCUSDT",
            "utc_month": "2020-01",
            "source_key": _key("daily/klines", "BTCUSDT", f"2020-01-{index // 2 + 1:02d}"),
            "source_state": sizing.RETAINED_RECEIPT_STATE,
            "source_sha256": f"{index:064x}",
            "checksum_authority": f"{index:064x}",
            # Half the mappings have a real retrieval time; half are honestly unknown.
            "retrieval_time": "2026-08-21T00:00:00+00:00" if index % 4 == 0 else None,
            "availability_semantics": "source_object_listing_time_unknown",
            "source_available_at": None,
            "requirement_byte_size": 500,
        }
        for index in range(8)
    ]
    manifest = measure_partition_manifest(
        entries, destination=tmp_path / "manifest.parquet"
    )
    assert manifest["payload_bytes_per_mapping"] > 0
    # One mapping per raw object per product partition, so a cross-product object
    # appears in both of its product partitions.
    assert manifest["mappings"] == 8
    assert manifest["rows"] == 8
    assert manifest["retrieval_time_known_mappings"] == 2
    assert manifest["retrieval_time_unknown_mappings"] == 6
    assert manifest["payload_bytes"] + manifest["footer_bytes"] + manifest[
        "framing_bytes"
    ] + manifest["residual_bytes"] == manifest["file_bytes"]
    assert manifest["payload_bytes"] > 0
    with pytest.raises(SizingError, match="has no raw object mapping"):
        measure_partition_manifest([], destination=tmp_path / "empty.parquet")


def test_no_cost_row_field_or_sample_is_reduced(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    """ADR-0024 section 1: the cost sample keeps every object, row, and field."""
    receipt = _run(accepted, tmp_path)["receipt"]
    assert receipt["physical_inputs"]["cost_objects"] == sizing.ACCEPTED_COST_OBJECTS
    assert receipt["physical_inputs"]["cost_bytes"] == sizing.ACCEPTED_COST_BYTES
    assert receipt["cohort"]["unique_samples"] == sizing.ACCEPTED_SAMPLE_COHORT
    with pytest.raises(SizingError, match="five-component descriptor"):
        sizing.final_product_schema("binance_usdm_cost_calibration")
    assert sizing.target_only_columns("binance_usdm_cost_calibration") == ()
    components = receipt["cost_calibration_components"]
    assert components["projected_bytes"] == sum(
        int(components[name]["projected_bytes"]) for name in sizing.COST_COMPONENTS
    )
    assert components["partition_count"] == sum(
        int(components[name]["partition_count"]) for name in sizing.COST_COMPONENTS
    )
    assert all(
        int(components[name]["catalog_pages"])
        == int(components[name]["partition_count"])
        for name in sizing.COST_COMPONENTS
    )
    # Every cost row of every cost sample is written typed, never sampled or summarised.
    for family in COST_FAMILIES:
        rows = 11
        payload = _zip("data.csv", _csv(family, rows))
        output = contributions_for_family(family)[0]
        measured = measure_typed_envelope(
            _cohort_sample(family),
            payload=payload,
            output=output,
            destination=tmp_path / f"cost-{family.replace('/', '_')}.parquet",
            schema_kind="headerless",
        )
        assert measured.rows == rows
        assert measured.source_rows == rows
        assert set(output.source_fields()) == set(
            KNOWN_ARCHIVE_SCHEMAS[_hint(family)]["headerless"]
        )
    measurements = {item["contribution"] for item in receipt["measurements"]}
    assert {
        "binance_usdm_cost_calibration:daily_book_ticker",
        "binance_usdm_cost_calibration:daily_book_depth",
    } <= measurements


def test_a_v2_envelope_collision_is_refused_not_overwritten(tmp_path: Path) -> None:
    root = tmp_path / sizing.SIZING_EVIDENCE_ROOT
    payload = _zip("data.csv", _csv("daily/bookDepth", 4))
    source = tmp_path / "envelope.parquet"
    measure_typed_envelope(
        _cohort_sample("daily/bookDepth"),
        payload=payload,
        output=contributions_for_family("daily/bookDepth")[0],
        destination=source,
        schema_kind="headerless",
    )
    destination, reused = sizing.publish_sizing_envelope(source, evidence_root=root)
    assert reused is False
    # Republishing identical bytes reuses the existing content address.
    _again, reused_again = sizing.publish_sizing_envelope(source, evidence_root=root)
    assert reused_again is True
    # A different file already occupying that content address is refused outright.
    destination.write_bytes(b"a conflicting occupant")
    with pytest.raises(SizingError, match="does not match its content address"):
        sizing.publish_sizing_envelope(source, evidence_root=root)
    assert destination.read_bytes() == b"a conflicting occupant"


def test_accepted_logical_aliases_fold_to_physical_bindings(
    accepted: dict[str, Any],
) -> None:
    """ADR-0025 section 4: a repeated key with identical lineage folds, never blocks."""
    authority = load_sizing_authority(accepted["paths"])
    cohort = derive_sample_cohort(authority)
    checkpoint = dict(authority.progress_checkpoint["objects"])
    lineage = bind_sample_lineage(
        authority.report, checkpoint=checkpoint, cohort=cohort
    )
    decomposition = lineage["decomposition"]
    records = accepted["sample_records"]
    aliases = accepted["alias_keys"]
    assert aliases
    assert decomposition["logical_records"] == len(records)
    assert decomposition["physical_bindings"] == len({r["key"] for r in records})
    assert decomposition["folded_aliases"] == len(aliases)
    # Logical minus physical is exactly the folded alias count.
    assert (
        decomposition["logical_records"] - decomposition["physical_bindings"]
        == decomposition["folded_aliases"]
    )
    proved = sizing.prove_accepted_lineage_decomposition(decomposition)
    assert proved["logical_records"] == sizing.ACCEPTED_LOGICAL_SAMPLE_RECORDS
    assert proved["physical_bindings"] == sizing.ACCEPTED_PHYSICAL_SAMPLE_BINDINGS
    assert proved["folded_aliases"] == sizing.ACCEPTED_FOLDED_SAMPLE_ALIASES
    # Every logical regime label survives on the folded physical record.
    folded = [
        item
        for item in lineage["bindings"].values()
        if item["logical_records"] > 1
    ]
    assert folded
    for item in folded:
        assert set(item["logical_regimes"]) == {"in_sample", "out_of_sample"}
        assert item["logical_roles"] == ["binance_usdm_bar_1h"]


def test_the_accepted_lineage_decomposition_is_pinned_at_106_96_10() -> None:
    assert sizing.ACCEPTED_LOGICAL_SAMPLE_RECORDS == 106
    assert sizing.ACCEPTED_PHYSICAL_SAMPLE_BINDINGS == 96
    assert sizing.ACCEPTED_FOLDED_SAMPLE_ALIASES == 10
    assert (
        sizing.ACCEPTED_LOGICAL_SAMPLE_RECORDS
        - sizing.ACCEPTED_PHYSICAL_SAMPLE_BINDINGS
        == sizing.ACCEPTED_FOLDED_SAMPLE_ALIASES
    )
    with pytest.raises(SizingError, match="lineage.logical_records"):
        sizing.prove_accepted_lineage_decomposition(
            {"logical_records": 96, "physical_bindings": 96, "folded_aliases": 0}
        )


@pytest.mark.parametrize(
    "field",
    [
        "sha256",
        "byte_size",
        "family",
        "retrieval_time",
        "availability_semantics",
        "source_available_at",
    ],
)
def test_a_disagreeing_alias_blocks_even_though_the_key_repeats(
    accepted: dict[str, Any], field: str
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    cohort = derive_sample_cohort(authority)
    checkpoint = dict(authority.progress_checkpoint["objects"])
    report = json.loads(accepted["files"]["report"].read_text())
    key = accepted["alias_keys"][0]
    seen = 0
    for record in report["samples"]:
        if record["key"] != key:
            continue
        seen += 1
        if seen == 2:
            record[field] = {
                "sha256": "0" * 64,
                "byte_size": 1,
                "family": "daily/metrics",
                "retrieval_time": "2026-08-22T00:00:00+00:00",
                "availability_semantics": "something_else",
                "source_available_at": 1,
            }[field]
    with pytest.raises(SizingError, match="disagrees about its physical lineage"):
        bind_sample_lineage(report, checkpoint=checkpoint, cohort=cohort)


def test_context_independent_conversion_survives_a_changed_decimal_context() -> None:
    """ADR-0025 section 3: no result may depend on the ambient decimal context."""
    boundary = "9" * (sizing.DECIMAL_PRECISION - sizing.DECIMAL_SCALE) + "." + "9" * (
        sizing.DECIMAL_SCALE
    )
    lexemes = [boundary, "0.1", "1e3", "-2.5E-3", "123456789012345678.999999999999999999"]
    reference: dict[str, Decimal] = {}
    for precision in (9, 28, 60):
        with localcontext() as context:
            context.prec = precision
            for token in lexemes:
                value = sizing.convert_decimal(
                    token, key="k", output="o", column="c", row=0
                )
                assert value.as_tuple().exponent == -sizing.DECIMAL_SCALE
                reference.setdefault(token, value)
                # Byte-identical under every context.
                assert value == reference[token]
                assert value.as_tuple() == reference[token].as_tuple()
    # One more digit than the pinned precision blocks under every context too.
    over = "9" * (sizing.DECIMAL_PRECISION - sizing.DECIMAL_SCALE + 1) + "." + "9" * (
        sizing.DECIMAL_SCALE
    )
    for precision in (9, 28, 60):
        with localcontext() as context:
            context.prec = precision
            with pytest.raises(SizingError, match="overflows the pinned precision"):
                sizing.convert_decimal(over, key="k", output="o", column="c", row=0)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1970-01-01 00:00:00", 0),
        ("2020-01-01 00:00:00", 1_577_836_800_000),
        ("1969-12-31 23:59:59", -1_000),
        ("1900-01-01 00:00:00", -2_208_988_800_000),
        ("2020-01-01T00:00:00.123456+00:00", 1_577_836_800_123),
        ("2020-01-01T01:00:00+01:00", 1_577_836_800_000),
    ],
)
def test_integer_calendar_timestamps_including_pre_epoch(
    text: str, expected: int
) -> None:
    for precision in (9, 60):
        with localcontext() as context:
            context.prec = precision
            value = sizing.convert_timestamp_text(
                text, key="k", output="o", column="c", row=0
            )
            assert value == expected
            assert isinstance(value, int)
    source = Path(sizing.__file__).read_text(encoding="utf-8")
    # The float-returning API is deliberately absent from this module.
    assert ".timestamp()" not in source


# Fields every product row carries by construction, so they are charged once per
# product row and necessarily recur across product schemas. They are identity and
# index labels, never product-specific derived fields.
_SHARED_SCHEMA_FIELDS: frozenset[str] = frozenset(
    {
        "venue",
        "native_symbol",
        "canonical_instrument_id",
        "canonical_instrument_version_id",
        "reference_identity_state",
        # The cross-product index label declared by both index products.
        "required_product",
    }
)


def test_final_product_schemas_are_complete_and_target_only_fields_are_allocated_once(
) -> None:
    allocated: dict[str, str] = {}
    for product in REQUIRED_PRODUCTS:
        if product == "binance_usdm_cost_calibration":
            with pytest.raises(SizingError, match="five-component descriptor"):
                sizing.final_product_columns(product)
            assert sizing.target_only_columns(product) == ()
            continue
        columns = sizing.final_product_columns(product)
        assert columns
        names = [column.name for column in columns]
        # Within one schema every field name is still allocated exactly once.
        assert len(set(names)) == len(names)
        for column in sizing.target_only_columns(product):
            if column.name in _SHARED_SCHEMA_FIELDS:
                continue
            # A product-specific target-only field belongs to exactly one product.
            assert column.name not in allocated or allocated[column.name] == product
            allocated.setdefault(column.name, product)
        for field in sizing.final_product_schema(product):
            assert field.type not in {pa.float32(), pa.float64()}
    # Every product row carries canonical instrument and contract-version identity.
    for product in REQUIRED_PRODUCTS:
        if product in {
            "binance_usdm_harmonic_bundle",
            "binance_usdm_cost_calibration",
        }:
            continue
        names = {column.name for column in sizing.final_product_columns(product)}
        assert {
            "venue",
            "native_symbol",
            "canonical_instrument_id",
            "canonical_instrument_version_id",
            "reference_identity_state",
        } <= names
    flow = {column.name for column in sizing.final_product_columns(
        "binance_usdm_trade_flow_1h"
    )}
    # Totals, taker-buy inputs, and the materialized sell/imbalance outputs.
    assert {
        "volume",
        "quote_volume",
        "taker_buy_volume",
        "taker_buy_quote_volume",
        "taker_sell_volume",
        "taker_sell_quote_volume",
        "volume_imbalance",
        "quote_volume_imbalance",
    } <= flow
    oi = {column.name: column for column in sizing.final_product_columns(
        "binance_usdm_open_interest_5m"
    )}
    assert {
        "sum_open_interest",
        "previous_sum_open_interest",
        "open_interest_change",
        "open_interest_value_change",
        "change_interval_seconds",
        "gap_break_status",
    } <= set(oi)
    assert oi["previous_sum_open_interest"].nullable is True
    funding = {column.name for column in sizing.final_product_columns(
        "binance_usdm_funding_realized"
    )}
    assert {"long_cashflow_rate", "short_cashflow_rate", "cashflow_sign_convention"} <= (
        funding
    )
    indicative = {column.name: column for column in sizing.final_product_columns(
        "binance_usdm_funding_indicative_1h"
    )}
    # No retained source publishes a direct indicative rate; it is nullable and gapped.
    assert indicative["indicative_funding_rate"].nullable is True
    assert "indicative_rate_status" in indicative
    basis = {column.name for column in sizing.final_product_columns(
        "binance_usdm_mark_index_basis_1h"
    )}
    assert {"mark_close", "index_close", "premium_close", "absolute_basis",
            "relative_basis", "basis_join_status"} <= basis
    liquidation = {column.name for column in sizing.final_product_columns(
        "binance_usdm_liquidation_observed_daily"
    )}
    assert {"provider_symbol", "long_liquidation", "short_liquidation",
            "liquidation_imbalance", "source_interval_seconds",
            "observation_semantics", "event_complete"} <= liquidation
    bundle = {column.name for column in sizing.final_product_columns(
        "binance_usdm_harmonic_bundle"
    )}
    assert {"dataset_id", "schema_sha256", "lineage_manifest_sha256",
            "lineage_mapping_count", "source_report_sha256",
            "qualification_cli_sha256", "sizing_cli_sha256",
            "configuration_sha256", "unit_convention", "censorship_semantics",
            "scenario_policy_sha256", "coverage_gap_rows",
            "cross_product_intersection_count",
            "cross_product_intersection_sha256"} <= bundle


def _cohort_of(families: dict[str, list[dict[str, Any]]], **keys: str) -> Any:
    return sizing.DerivationCohort(
        native_symbol="BTCUSDT",
        economic_interval="2020-01-01",
        families=families,
        keys=keys or {family: "k" for family in families},
    )


def _kline_row(ordinal: int = 0, **overrides: str) -> dict[str, Any]:
    row = {
        "open_time": str(1577836800000 + ordinal * 3_600_000),
        "open": "1.0",
        "high": "2.0",
        "low": "0.5",
        "close": "1.5",
        "volume": "10",
        "close_time": str(1577840399999 + ordinal * 3_600_000),
        "quote_volume": "15.0",
        "count": "7",
        "taker_buy_volume": "4.0",
        "taker_buy_quote_volume": "6.0",
        "ignore": "0",
        "_ordinal": ordinal,
        "_symbol": "BTCUSDT",
        "_economic_interval": "2020-01-01",
        "_key": "k",
    }
    row.update(overrides)
    return row


def test_derived_columns_are_computed_from_real_sample_values() -> None:
    cohort = _cohort_of({"daily/klines": [_kline_row()]})
    rows = sizing.derive_target_only_rows("binance_usdm_trade_flow_1h", cohort=cohort)
    assert len(rows) == 1
    row = rows[0]
    # Real arithmetic on the real sample values, not a constant or a null.
    assert row["taker_sell_volume"] == Decimal("6")
    assert row["taker_sell_quote_volume"] == Decimal("9")
    assert row["volume_imbalance"] == Decimal("-2")
    assert row["quote_volume_imbalance"] == Decimal("-3")
    # No ticker-derived canonical identity is ever published as reference truth.
    assert row["canonical_instrument_id"] is None
    assert row["canonical_instrument_version_id"] is None
    assert row["reference_identity_state"] == "reference_identity_not_yet_created"
    assert row["native_symbol"] == "BTCUSDT"


def _basis_cohort(mark: str, index: str, *, shift: int = 0) -> Any:
    return _cohort_of(
        {
            "daily/markPriceKlines": [_kline_row(close=mark, open=mark)],
            "daily/indexPriceKlines": [
                _kline_row(ordinal=shift, close=index, open=index)
            ],
            "daily/premiumIndexKlines": [_kline_row(close="0.1", open="0.1")],
        }
    )


def test_relative_basis_is_deterministic_and_rejects_a_zero_denominator() -> None:
    for precision in (9, 28, 60):
        with localcontext() as context:
            context.prec = precision
            rows = sizing.derive_target_only_rows(
                "binance_usdm_mark_index_basis_1h",
                cohort=_basis_cohort("100.5", "100.0"),
            )
            assert rows[0]["absolute_basis"] == Decimal("0.5")
            assert rows[0]["relative_basis"] == Decimal("0.005")
            assert rows[0]["basis_join_status"] == "causal_open_time_join"
    with pytest.raises(SizingError, match="zero index denominator"):
        sizing.derive_target_only_rows(
            "binance_usdm_mark_index_basis_1h", cohort=_basis_cohort("100.5", "0")
        )


def test_basis_never_joins_mismatched_times_or_a_missing_premium_input() -> None:
    """Review 236 finding 3: an ordinal is not a causal join."""
    # Same ordinal, different open/close time: no row may be produced.
    shifted = sizing.derive_target_only_rows(
        "binance_usdm_mark_index_basis_1h",
        cohort=_basis_cohort("100.5", "100.0", shift=3),
    )
    assert shifted == []
    # Matching times but no premium input for that instant: still no causal join.
    families = {
        "daily/markPriceKlines": [_kline_row(close="100.5", open="100.5")],
        "daily/indexPriceKlines": [_kline_row(close="100.0", open="100.0")],
        "daily/premiumIndexKlines": [_kline_row(ordinal=5, close="0.1", open="0.1")],
    }
    assert sizing.derive_target_only_rows(
        "binance_usdm_mark_index_basis_1h", cohort=_cohort_of(families)
    ) == []
    # A cohort missing a whole family produces nothing rather than a partial join.
    assert sizing.derive_target_only_rows(
        "binance_usdm_mark_index_basis_1h",
        cohort=_cohort_of({"daily/markPriceKlines": [_kline_row()]}),
    ) == []


def test_an_open_interest_gap_nulls_the_previous_comparable_and_changes() -> None:
    def _metric(ordinal: int, minutes: int, level: str) -> dict[str, Any]:
        return {
            "create_time": f"2020-01-01 00:{minutes:02d}:00",
            "symbol": "BTCUSDT",
            "sum_open_interest": level,
            "sum_open_interest_value": level,
            "count_toptrader_long_short_ratio": "1",
            "sum_toptrader_long_short_ratio": "1",
            "count_long_short_ratio": "1",
            "sum_taker_long_short_vol_ratio": "1",
            "_ordinal": ordinal,
            "_symbol": "BTCUSDT",
            "_economic_interval": "2020-01-01",
            "_key": "k",
        }

    cohort = _cohort_of(
        {
            "daily/metrics": [
                _metric(0, 0, "10"),
                _metric(1, 5, "12"),
                # A ten-minute step is a discontinuity in a five-minute grid.
                _metric(2, 15, "20"),
            ]
        }
    )
    rows = sizing.derive_target_only_rows("binance_usdm_open_interest_5m", cohort=cohort)
    assert [row["gap_break_status"] for row in rows] == [
        "first_observation",
        "contiguous",
        "gap_break",
    ]
    assert rows[0]["previous_sum_open_interest"] is None
    assert rows[1]["previous_sum_open_interest"] == Decimal("10")
    assert rows[1]["open_interest_change"] == Decimal("2")
    assert rows[1]["change_interval_seconds"] == 300
    # The gap publishes the observed interval and status but no comparable or change.
    assert rows[2]["change_interval_seconds"] == 600
    assert rows[2]["previous_sum_open_interest"] is None
    assert rows[2]["open_interest_change"] is None
    assert rows[2]["open_interest_value_change"] is None


def test_two_partitions_each_pay_their_own_full_manifest_overhead(
    tmp_path: Path,
) -> None:
    """Review 236 finding 6: no cohort-global manifest divided by its own row count."""
    def _mapping(product: str, symbol: str, month: str, index: int) -> dict[str, Any]:
        return {
            "raw_object_ref": index,
            "required_product": product,
            "component": "daily_klines",
            "native_symbol": symbol,
            "utc_month": month,
            "source_key": _key("daily/klines", symbol, f"{month}-01"),
            "source_state": sizing.RETAINED_RECEIPT_STATE,
            "source_sha256": f"{index:064x}",
            "checksum_authority": f"{index:064x}",
            "retrieval_time": None,
            "availability_semantics": "source_object_listing_time_unknown",
            "source_available_at": None,
            "requirement_byte_size": 500,
        }

    small = {("binance_usdm_bar_1h", "target_product", "BTCUSDT", "2020-01"): [
        _mapping("binance_usdm_bar_1h", "BTCUSDT", "2020-01", 0)
    ]}
    large = {("binance_usdm_bar_1h", "target_product", "ETHUSDT", "2020-02"): [
        _mapping("binance_usdm_bar_1h", "ETHUSDT", "2020-02", index)
        for index in range(6)
    ]}
    model = sizing.model_partition_lineage({**small, **large}, staging=tmp_path)
    assert model.payload_bytes_per_mapping > 0
    assert model.footer_per_row_group_bytes > 0
    assert model.framing_bytes == 12
    # Two real, differently sized witnesses were measured, not one cohort file.
    assert len(model.witness_partitions) == 2
    assert {int(item["mappings"]) for item in model.witness_partitions} == {1, 6}
    archive_row = sizing.pq.read_table(
        str(tmp_path / "lineage-archive-partition-0.parquet")
    ).to_pylist()[0]
    assert archive_row["required_product"] == "binance_usdm_bar_1h"
    assert archive_row["component"] == "daily_klines"
    assert archive_row["native_symbol"] == "BTCUSDT"
    assert archive_row["utc_month"] == "2020-01"
    assert archive_row["source_state"] == sizing.RETAINED_RECEIPT_STATE
    one = model.partition_bytes(1)
    six = model.partition_bytes(6)
    fixed = model.footer_per_row_group_bytes + model.framing_bytes
    # Exact sums: each partition pays the full fixed overhead, once.
    assert one["bytes"] == model.payload_bytes_per_mapping + fixed
    assert six["bytes"] == 6 * model.payload_bytes_per_mapping + fixed
    assert one["bytes"] + six["bytes"] == (
        7 * model.payload_bytes_per_mapping + 2 * fixed
    )
    # The rejected model would have divided a single file by its rows and charged the
    # fixed overhead only once across both partitions.
    assert one["bytes"] + six["bytes"] > 7 * model.payload_bytes_per_mapping + fixed


def test_coinalyze_partitions_carry_receipt_and_provider_native_mappings(
    accepted: dict[str, Any], tmp_path: Path,
) -> None:
    resolved = _coinalyze(accepted)
    natives = accepted["anchor_natives"]
    mapped = sizing.coinalyze_partition_lineage(
        partitions=[(native, "2020-01") for native in natives]
        + [(natives[0], "2020-02")],
        receipt_sha256="a" * 64,
        receipt_endpoint="/liquidation-history",
        identities=resolved["identities"],
        availability="retained_coinalyze_response_receipt",
        retrieval_time=None,
        retained_partitions=[(native, "2020-01") for native in natives],
    )
    assert len(mapped) == len(natives) + 1
    for (product, component, symbol, month), mappings in mapped.items():
        assert product == "binance_usdm_liquidation_observed_daily"
        assert component == "observed_liquidation"
        assert month in {"2020-01", "2020-02"}
        row = mappings[0]
        # The local reference maps to the response receipt and the proved pair.
        if month == "2020-01":
            assert row["source_sha256"] == "a" * 64
            assert row["source_state"] == sizing.RETAINED_RECEIPT_STATE
        else:
            assert row["source_sha256"] is None
            assert row["checksum_authority"] is None
            assert row["source_state"] == sizing.PROJECTED_UNACQUIRED_STATE
        assert row["source_key"].startswith("/liquidation-history#")
        assert row["native_symbol"] == symbol
        assert row["provider_symbol"] == accepted["provider_of"][symbol]
        assert row["availability_semantics"] in {
            "retained_coinalyze_response_receipt",
            "projected_response_receipt",
        }
        assert row["retrieval_time"] is None
    measured = measure_partition_manifest(
        next(iter(mapped.values())), destination=tmp_path / "coinalyze-manifest.parquet"
    )
    coinalyze_row = sizing.pq.read_table(
        str(tmp_path / "coinalyze-manifest.parquet")
    ).to_pylist()[0]
    assert measured["manifest_kind"] == "coinalyze"
    assert coinalyze_row["component"] == "observed_liquidation"
    assert coinalyze_row["provider_symbol"]
    assert coinalyze_row["native_symbol"]
    assert coinalyze_row["utc_month"] == "2020-01"


def test_archive_lineage_retention_joins_only_to_the_disjoint_credit_set() -> None:
    objects = _one_object_per_family()
    coefficient = objects[0]
    credited = objects[-1]
    assert coefficient.key != credited.key
    checkpoint = {
        credited.key: {
            "status": "complete",
            "sha256": "a" * 64,
            "byte_size": credited.byte_size,
            "provider_checksum_sha256": "b" * 64,
            "retrieval_time": "2026-08-21T00:00:00+00:00",
        }
    }
    credit = {
        "keys": [credited.key],
        "valid_requirement_keys": 1,
        "key_set_sha256": sizing.requirement_key_set_sha256([credited.key]),
    }
    # The coefficient key is deliberately disjoint and supplies no retention authority.
    bindings = sizing.build_retained_archive_bindings(
        credit=credit,
        checkpoint=checkpoint,
        objects=objects,
        sample_bindings={
            coefficient.key: {
                "source_key": coefficient.key,
                "source_sha256": "c" * 64,
            }
        },
    )
    assert set(bindings) == {credited.key}
    partitions = sizing.build_partition_lineage(
        bindings,
        objects=objects,
        retained_credit_keys=credit["keys"],
    )
    # Every partition key is a real product / native symbol / UTC month triple.
    for product, component, symbol, month in partitions:
        assert product in REQUIRED_PRODUCTS
        assert component in {
            "target_product",
            "retained_book_ticker",
            "retained_book_depth",
        }
        assert symbol == "BTCUSDT"
        assert month == "2020-01"
    # A kline object feeds two products, so it is mapped in both partitions.
    assert sum(len(value) for value in partitions.values()) == sum(
        len(contributions_for_family(item.family)) for item in objects
    )
    states = {
        str(row["source_key"]): str(row["source_state"])
        for mappings in partitions.values()
        for row in mappings
    }
    assert states[credited.key] == sizing.RETAINED_RECEIPT_STATE
    assert states[coefficient.key] == sizing.PROJECTED_UNACQUIRED_STATE
    assert all(
        state == sizing.PROJECTED_UNACQUIRED_STATE
        for key, state in states.items()
        if key != credited.key
    )
    reconciliation = sizing.reconcile_archive_lineage(
        partitions,
        requirement_keys=[item.key for item in objects],
        retained_credit_keys=credit["keys"],
        coefficient_keys=[coefficient.key],
    )
    assert reconciliation["retained_archive_requirement_keys"] == 1
    assert reconciliation["retained_archive_key_set_sha256"] == credit[
        "key_set_sha256"
    ]
    assert reconciliation["projected_unacquired_archive_requirement_keys"] == (
        len(objects) - 1
    )
    assert reconciliation["coefficient_only_keys_marked_retained"] == 0
    assert len(partitions) == len(
        {item.product for item in sizing.PRODUCT_CONTRIBUTIONS}
    ) + 1  # ticker and depth are independent cost partitions
    with pytest.raises(SizingError, match="exact checkpoint binding"):
        sizing.build_retained_archive_bindings(
            credit=credit,
            checkpoint={},
            objects=objects,
            sample_bindings={},
        )
    with pytest.raises(SizingError, match="credited_sample.source_sha256"):
        sizing.build_retained_archive_bindings(
            credit=credit,
            checkpoint=checkpoint,
            objects=objects,
            sample_bindings={
                credited.key: {
                    **bindings[credited.key],
                    "source_sha256": "d" * 64,
                    "byte_size": credited.byte_size,
                    "family": credited.family,
                }
            },
        )
    with pytest.raises(SizingError, match="retained_lineage_credit_join"):
        sizing.build_partition_lineage(
            {
                **bindings,
                coefficient.key: {
                    **bindings[credited.key],
                    "source_key": coefficient.key,
                },
            },
            objects=objects,
            retained_credit_keys=credit["keys"],
        )


def test_a_credited_retained_object_may_be_smaller_than_its_requirement_listing() -> None:
    """ADR-0023 keeps two byte facts apart, and both stay exact.

    The credited checkpoint value is the real retained content-addressed object length
    already rehashed against the bytes on disk. `PhysicalObject.byte_size` is the
    complete acquisition-requirement listing size. A retained cost witness is routinely
    the smaller of the two, so equality would be false authority rather than a check.
    """
    requirement_bytes = 2_072
    retained_bytes = 145
    objects = _one_object_per_family(requirement_bytes)
    credited = objects[-1]
    assert credited.byte_size == requirement_bytes != retained_bytes
    checkpoint = {
        credited.key: {
            "status": "complete",
            "sha256": "a" * 64,
            "byte_size": retained_bytes,
            "provider_checksum_sha256": "b" * 64,
            "retrieval_time": "2026-08-21T00:00:00+00:00",
        }
    }
    credit = {
        "keys": [credited.key],
        "valid_requirement_keys": 1,
        "key_set_sha256": sizing.requirement_key_set_sha256([credited.key]),
    }
    sample = {
        "source_key": credited.key,
        "source_sha256": "a" * 64,
        # The accepted report sample records the same retained object, so it carries
        # the retained length, never the requirement listing size.
        "byte_size": retained_bytes,
        "family": credited.family,
        "checksum_authority": "b" * 64,
        "retrieval_time": "2026-08-21T00:00:00+00:00",
        "availability_semantics": "source_object_listing_time_unknown",
        "source_available_at": None,
    }
    bindings = sizing.build_retained_archive_bindings(
        credit=credit,
        checkpoint=checkpoint,
        objects=objects,
        sample_bindings={credited.key: sample},
    )
    bound = bindings[credited.key]
    # Both facts survive, separately named and independently correct.
    assert bound["retained_byte_size"] == retained_bytes
    assert bound["requirement_byte_size"] == requirement_bytes
    assert bound["source_sha256"] == "a" * 64
    assert bound["checksum_authority"] == "b" * 64
    # Neither value is derived from the other by subtraction or relabelling.
    assert bound["retained_byte_size"] != bound["requirement_byte_size"]
    # The projected manifest keeps serializing the requirement listing size.
    partitions = sizing.build_partition_lineage(
        bindings,
        objects=objects,
        retained_credit_keys=credit["keys"],
    )
    mapped = [
        row
        for mappings in partitions.values()
        for row in mappings
        if row["source_key"] == credited.key
    ]
    assert mapped
    assert {row["requirement_byte_size"] for row in mapped} == {requirement_bytes}
    assert {row["source_state"] for row in mapped} == {sizing.RETAINED_RECEIPT_STATE}
    # A sample binding claiming the requirement listing size instead of the real
    # retained length is still rejected by name.
    with pytest.raises(SizingError, match="credited_sample.byte_size"):
        sizing.build_retained_archive_bindings(
            credit=credit,
            checkpoint=checkpoint,
            objects=objects,
            sample_bindings={
                credited.key: {**sample, "byte_size": requirement_bytes}
            },
        )
    # A retained length that is absent or not a positive integer still blocks.
    for damaged in (0, -1, None, "145"):
        with pytest.raises(SizingError, match="credited_checkpoint.byte_size"):
            sizing.build_retained_archive_bindings(
                credit=credit,
                checkpoint={
                    credited.key: {**checkpoint[credited.key], "byte_size": damaged}
                },
                objects=objects,
                sample_bindings={credited.key: sample},
            )


def test_lineage_overhead_is_charged_once_per_partition(tmp_path: Path) -> None:
    """ADR-0025 section 5: never one cohort file divided by its own row count."""
    model = _lineage_model(payload=3, footer=90, framing=12)
    one = model.partition_bytes(1)
    many = model.partition_bytes(4)
    # Payload scales with mappings; the file overhead is charged once per partition.
    assert one["payload_bytes"] == 3
    assert many["payload_bytes"] == 12
    assert one["overhead_bytes"] == many["overhead_bytes"] == 90 + 12
    assert one["bytes"] == 105
    assert many["bytes"] == 114
    # Two real partitions each carry their own overhead, so the small one is not
    # undercounted by the exact amount ADR-0024 required to separate.
    objects = _one_object_per_family()
    projections = project_typed_partitions(
        measurements=_all_measurements(),
        objects=objects,
        lineage=model,
    )
    for item in projections:
        expected = sum(
            model.partition_bytes(int(partition["mappings"]))["bytes"]
            for partition in item.partitions
        )
        assert item.projected_manifest_bytes == expected


def test_the_membership_boundary_splits_accepted_from_rejected(
    accepted: dict[str, Any],
) -> None:
    """Review 236 finding 1: classifications are not all accepted identities."""
    report = json.loads(accepted["files"]["report"].read_text())
    membership = sizing.classify_membership(report)
    counts = membership["counts"]
    total = len(accepted["classifications"])
    granted = len(accepted["accepted_membership"])
    assert counts["membership_classifications"] == total
    assert counts["accepted_membership_identities"] == granted
    assert counts["rejected_membership_rows"] == total - granted
    assert counts["rejected_membership_rows"] > 0
    # Every accepted row is affirmatively confirmed; no rejected row is admitted.
    assert all(
        str(row["membership_class"]) == "confirmed_perpetual"
        for row in membership["accepted"]
    )
    assert all(row.get("accepted") is not True for row in membership["rejected"])
    rejected_symbols = {str(row["symbol"]) for row in membership["rejected"]}
    accepted_symbols = {str(row["symbol"]) for row in membership["accepted"]}
    assert not rejected_symbols & accepted_symbols


def test_rejected_membership_rows_create_no_fee_gap_or_membership_row(
    accepted: dict[str, Any],
) -> None:
    report = json.loads(accepted["files"]["report"].read_text())
    coverage = sizing.prove_coverage_authority(report)
    rejected = {
        str(row["symbol"]) for row in coverage["membership"]["rejected"]
    }
    assert rejected
    fee_symbols = {str(row["native_symbol"]) for row in coverage["fee_gaps"]}
    assert not fee_symbols & rejected
    assert len(coverage["fee_gaps"]) == len(accepted["accepted_membership"])
    assert coverage["counts"]["fee_authority_gaps"] == len(
        coverage["membership"]["accepted"]
    )


def test_membership_fields_come_from_accepted_evidence_including_non_usdt(
    accepted: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = json.loads(accepted["files"]["report"].read_text())
    membership = sizing.classify_membership(report)
    facts = {
        str(row["symbol"]): sizing.contract_evidence(row)
        for row in membership["accepted"]
    }
    # A non-USDT margin and settlement contract survives with its real assets.
    usdc = facts["BTCUSDC"]
    assert usdc["margin_asset"] == "USDC"
    assert usdc["quote_asset"] == "USDC"
    assert usdc["base_asset"] == "BTC"
    assert usdc["contract_type"] == "PERPETUAL"
    # No ticker-derived canonical identity is published anywhere.
    identity = sizing.native_identity("BTCUSDC")
    assert identity["canonical_instrument_id"] is None
    assert identity["canonical_instrument_version_id"] is None
    assert identity["reference_identity_state"] == "reference_identity_not_yet_created"
    assert "BTCUSDC" not in str(identity["reference_identity_state"])
    # The future REF widths are allocated explicitly, as widths.
    allocation = sizing.future_reference_identity_bytes(10)
    assert allocation["value_widths"]["canonical_instrument_id"] == 68
    assert allocation["value_widths"]["canonical_instrument_version_id"] == 67
    assert allocation["bytes"] == 10 * ((68 + 9) + (67 + 9))
    assert "not an existing canonical id" in allocation["allocation"]
    funding = sizing.contract_evidence(
        {
            "symbol": "ARCHIVEONLY",
            "membership_class": "confirmed_perpetual",
            "in_archive": True,
            "in_current_exchange": False,
            "evidence": [
                {
                    "kind": "official_realized_funding_observation",
                    "families": ["monthly/fundingRate"],
                    "semantics": "only a perpetual contract realizes funding",
                    "example_key": "data/futures/um/monthly/fundingRate/ARCHIVEONLY/x.zip",
                }
            ],
        }
    )
    assert funding["contract_type"] == "PERPETUAL"
    assert funding["contract_metadata_state"] == sizing.MEMBERSHIP_FUNDING_ONLY_STATE
    assert all(
        funding[name] is None
        for name in (
            "contract_status",
            "base_asset",
            "quote_asset",
            "margin_asset",
            "pair",
            "onboard_ms",
            "delivery_ms",
            "closed_observed_ms",
        )
    )
    monkeypatch.setattr(sizing, "ACCEPTED_FUNDING_ONLY_MEMBERSHIP_IDENTITIES", 1)
    unresolved = sizing.future_membership_term_bytes([funding])
    assert unresolved["rows"] == 1
    assert unresolved["bytes"] > len("ARCHIVEONLY") * 6
    source = Path(sizing.__file__).read_text(encoding="utf-8")
    assert "BINANCE_USDM:{" not in source
    assert "canonical_instrument_id(" not in source


def test_conflicting_accepted_evidence_blocks(accepted: dict[str, Any]) -> None:
    report = json.loads(accepted["files"]["report"].read_text())
    row = dict(
        next(
            item
            for item in report["membership"]["classifications"]
            if item.get("accepted") is True
        )
    )
    row["evidence"] = list(row["evidence"]) + [
        {**dict(row["evidence"][0]), "margin_asset": "BUSD"}
    ]
    with pytest.raises(SizingError, match="disagrees about a contract fact"):
        sizing.contract_evidence(row)
    # An accepted identity with no evidence at all also blocks.
    with pytest.raises(SizingError, match="has no evidence"):
        sizing.contract_evidence({"symbol": "BTCUSDT", "evidence": []})


def test_every_final_writer_round_trips_its_own_schema(tmp_path: Path) -> None:
    """Review 236 finding 3 and 4: a declared schema must be constructible."""
    points = [
        {
            "event_time_ms": 1577836800000,
            "event_time_seconds": 1577836800,
            "long_liquidation": sizing.convert_decimal(
                "1.5", key="k", output="o", column="c", row=0
            ),
            "short_liquidation": sizing.convert_decimal(
                "0.5", key="k", output="o", column="c", row=0
            ),
        }
    ]
    envelope = write_liquidation_envelope(
        symbol="BTCUSDT",
        provider_symbol="BTCUSDT_PERP.A",
        endpoint="/liquidation-history",
        points=points,
        destination=tmp_path / "liq.parquet",
    )
    table = sizing.pq.read_table(str(tmp_path / "liq.parquet"))
    schema = sizing.final_product_schema("binance_usdm_liquidation_observed_daily")
    assert table.schema.names == schema.names
    row = table.to_pylist()[0]
    assert row["native_symbol"] == "BTCUSDT"
    assert row["provider_symbol"] == "BTCUSDT_PERP.A"
    assert row["canonical_instrument_id"] is None
    assert row["liquidation_imbalance"] == Decimal("1.000000000000000000")
    assert row["source_interval_seconds"] == 86_400
    assert row["event_complete"] is False
    assert row["observation_semantics"] == "censored_observed_daily_aggregate"
    assert envelope["required_product"] == "binance_usdm_liquidation_observed_daily"
    # All five cost components declare their own constructible schema.
    assert sizing.COST_COMPONENTS == (
        "retained_book_ticker",
        "retained_book_depth",
        "official_fee_schedule",
        "fee_authority_gap",
        "scenario_policy",
    )
    for component in sizing.COST_COMPONENTS:
        columns = sizing.cost_component_columns(component)
        assert columns
        component_schema = sizing._schema_of(columns)
        assert len(component_schema.names) == len(columns)
        assert len(set(component_schema.names)) == len(columns)
    # The heterogeneous components are not one flattened row shape.
    ticker = {c.name for c in sizing.cost_component_columns("retained_book_ticker")}
    scenario = {c.name for c in sizing.cost_component_columns("scenario_policy")}
    assert not ticker & scenario
    official = {c.name for c in sizing.cost_component_columns("official_fee_schedule")}
    assert {
        "valid_from_ms",
        "available_from_ms",
        "fee_tier",
        "evidence_sha256",
    } <= official
    with pytest.raises(SizingError, match="unknown cost component"):
        sizing.cost_component_columns("not_a_component")


ACCEPTED_STORE = Path("data/cex002_qualify")
ACCEPTED_REPORT = Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json")


def _accepted_authority_paths(
    detail: Path, *, store_root: Path = ACCEPTED_STORE
) -> AuthorityPaths:
    """The already accepted local authority, exactly as the CLI resolves it."""
    repository = Path.cwd()
    return AuthorityPaths(
        store_root=store_root,
        report_path=ACCEPTED_REPORT,
        manifest_detail_path=detail,
        qualification_source_path=repository
        / "src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py",
        qualification_cli_path=repository
        / "scripts/research/qualify_binance_usdm_harmonic_sources.py",
        lock_path=ACCEPTED_STORE / "cex002_sample_plan_lock.json",
        amendment_ledger_path=ACCEPTED_STORE / "cex002_amendment_ledger.json",
        progress_checkpoint_path=ACCEPTED_STORE / "cex002_qualification_progress.json",
        listing_checkpoint_path=ACCEPTED_STORE / "cex002_listing_checkpoint.json",
        contract_metadata_path=ACCEPTED_STORE / "cex002_official_contract_metadata.json",
        listing_cache_dir=ACCEPTED_STORE / "list_cache",
        coinalyze_cache_dir=ACCEPTED_STORE / "coinalyze_cache",
        sample_dir=ACCEPTED_STORE / "raw" / "sha256",
        sidecar_dir=ACCEPTED_STORE / "list_cache",
    )


def _accepted_manifest_detail() -> Path | None:
    root = ACCEPTED_STORE / "evidence" / "qualification"
    if not root.is_dir():
        return None
    for candidate in sorted(root.rglob("*.jsonl.gz")):
        if _sha256(candidate.read_bytes()) == sizing.ACCEPTED_MANIFEST_DETAIL_SHA256:
            return candidate
    return None


def test_the_real_accepted_authority_passes_the_membership_boundary() -> None:
    """The 1,008-total / 771-accepted split, read from the pinned local report."""
    if not ACCEPTED_REPORT.is_file():
        pytest.skip("the accepted local qualification report is not present")
    report = json.loads(ACCEPTED_REPORT.read_text())
    rows = list(dict(report.get("membership") or {}).get("classifications") or ())
    granted = [item for item in rows if item.get("accepted") is True]
    # The real split, not a constant comparison and not a synthetic fixture.
    assert len(rows) == 1_008
    assert len(granted) == 771
    assert len(rows) - len(granted) == 237
    membership = sizing.classify_membership(report)
    assert membership["counts"] == {
        "membership_classifications": 1_008,
        "accepted_membership_identities": 771,
        "rejected_membership_rows": 237,
    }
    coverage = sizing.prove_coverage_authority(report)
    counts = coverage["counts"]
    assert counts["accepted_source_coverage_gaps"] == 8_317
    assert counts["accepted_typed_gap_memberships"] == 3_742
    assert counts["fee_authority_gaps"] == 771
    assert counts["known_coverage_rows"] == 9_088
    states: dict[str, int] = {}
    # Every one of the 771 identities is executable, including the 73 whose official
    # realized-funding evidence proves PERPETUAL but no unavailable ticker term.
    for row in membership["accepted"]:
        facts = sizing.contract_evidence(row)
        states[facts["contract_metadata_state"]] = (
            states.get(facts["contract_metadata_state"], 0) + 1
        )
        assert facts["contract_type"] == "PERPETUAL"
        assert facts["contract_evidence_class"]
        assert facts["contract_evidence_source"]
        if facts["contract_metadata_state"] == sizing.MEMBERSHIP_FUNDING_ONLY_STATE:
            assert facts["base_asset"] is None
            assert facts["quote_asset"] is None
            assert facts["margin_asset"] is None
            assert facts["pair"] is None
    assert states == {
        sizing.MEMBERSHIP_DETAILED_STATE: 698,
        sizing.MEMBERSHIP_FUNDING_ONLY_STATE: 73,
    }


def test_the_real_accepted_authority_completes_the_receipt_path(
    tmp_path: Path,
) -> None:
    """The full sizing path over the accepted local authority, published to a tmp root."""
    detail = _accepted_manifest_detail()
    if not ACCEPTED_REPORT.is_file() or detail is None:
        pytest.skip("the accepted local qualification authority is not present")
    temporary_store = tmp_path / "store"
    temporary_store.mkdir()
    paths = _accepted_authority_paths(detail, store_root=temporary_store)
    result = run_storage_sizing(
        paths,
        # Both the receipt and every envelope publish only beneath tmp_path. Authority
        # inputs remain pinned to their accepted read-only locations.
        receipt_path=tmp_path / "231_receipt.json",
        sizing_source_path=Path(sizing.__file__),
        sizing_cli_path=Path("scripts/research/size_binance_usdm_harmonic_release.py"),
        now=datetime(2026, 8, 23, tzinfo=UTC),
    )
    receipt = result["receipt"]
    assert receipt["schema_version"] == "cex002_gate2_storage_sizing_v2"
    counts = receipt["counts"]
    assert counts["membership_classifications"] == 1_008
    assert counts["accepted_membership_identities"] == 771
    assert counts["rejected_membership_rows"] == 237
    assert receipt["coverage_authority"]["known_coverage_rows"] == 9_088
    assert receipt["lineage"]["logical_records"] == 106
    assert receipt["lineage"]["physical_bindings"] == 96
    assert receipt["lineage"]["folded_aliases"] == 10
    credit = receipt["physical_inputs"]["retained_credit"]
    archive_lineage = receipt["lineage"]
    assert archive_lineage["retained_archive_requirement_keys"] == 73
    assert archive_lineage["retained_archive_requirement_keys"] == credit[
        "valid_requirement_keys"
    ]
    assert archive_lineage["retained_archive_key_set_sha256"] == credit[
        "key_set_sha256"
    ]
    assert credit["key_set_sha256"] == sizing.requirement_key_set_sha256(
        credit["keys"]
    )
    assert archive_lineage["projected_unacquired_archive_requirement_keys"] == (
        receipt["physical_inputs"]["combined_objects"] - 73
    )
    assert archive_lineage["coefficient_only_archive_keys"] > 0
    assert archive_lineage["coefficient_only_keys_marked_retained"] == 0
    assert receipt["future_width_allocations"]["membership_terms"]["rows"] == 73
    assert receipt["future_width_allocations"]["membership_terms"]["bytes"] > 0
    assert receipt["capacity"]["total_future_storage_bytes"] > 0
    assert Path(receipt["filesystem"]["destination"]) == temporary_store
    assert (temporary_store / sizing.SIZING_EVIDENCE_ROOT).is_dir()
    assert receipt["storage_preflight_state"] in {STATE_SUFFICIENT, STATE_BLOCKED}
    assert (tmp_path / "231_receipt.json").is_file()
    # A byte-identical rerun against the same authority reproduces the same receipt.
    again = run_storage_sizing(
        paths,
        receipt_path=tmp_path / "231_receipt.json",
        sizing_source_path=Path(sizing.__file__),
        sizing_cli_path=Path("scripts/research/size_binance_usdm_harmonic_release.py"),
        now=datetime(2026, 8, 24, tzinfo=UTC),
    )
    assert again["publication"]["rerun"] is True
    assert again["receipt_file"]["receipt_sha256"] == (
        result["receipt_file"]["receipt_sha256"]
    )


def test_the_bundle_descriptor_invents_no_witness(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    report = json.loads(accepted["files"]["report"].read_text())
    coverage = sizing.prove_coverage_authority(report)
    partitions = [
        {
            "required_product": "binance_usdm_bar_1h",
            "component": "target_product",
            "native_symbol": "BTCUSDT",
            "utc_month": "2020-01",
            "mappings": 3,
        },
        {
            "required_product": "binance_usdm_trade_flow_1h",
            "component": "target_product",
            "native_symbol": "ETHUSDT",
            "utc_month": "2020-02",
            "mappings": 1,
        },
    ]
    schemas = {
        f"{item['required_product']}:{item['component']}": (
            sizing.partition_schema_identity(item["required_product"], item["component"])
        )
        for item in partitions
    }
    descriptor = sizing.measure_bundle_descriptor(
        partitions=partitions,
        coverage=coverage,
        schema_identities=schemas,
        sizing_source_sha256="b" * 64,
        sizing_cli_sha256="c" * 64,
        intersections=(("BTCUSDT", "2020-01"), ("ETHUSDT", "2020-02")),
        staging=tmp_path,
    )
    table = sizing.pq.read_table(str(tmp_path / "product-bundle.parquet"))
    rows = table.to_pylist()
    assert len(rows) == 2
    for row in rows:
        # Nothing that only exists after Gate-3 publication is invented here.
        assert row["partition_sha256"] is None
        assert row["partition_bytes"] is None
        assert row["row_count"] is None
        assert row["lineage_manifest_sha256"] is None
        assert row["canonical_instrument_id"] is None
        assert row["partition_sha256"] != "0" * 64
        # Every identity that already exists is pinned exactly.
        assert row["source_report_sha256"] == sizing.ACCEPTED_REPORT_SHA256
        assert row["source_manifest_detail_sha256"] == (
            sizing.ACCEPTED_MANIFEST_DETAIL_SHA256
        )
        assert row["qualification_code_sha256"] == (
            sizing.ACCEPTED_QUALIFICATION_SOURCE_SHA256
        )
        assert row["qualification_cli_sha256"] == (
            sizing.ACCEPTED_QUALIFICATION_CLI_SHA256
        )
        assert row["sizing_code_sha256"] == "b" * 64
        assert row["sizing_cli_sha256"] == "c" * 64
        assert row["schema_sha256"] == schemas[
            f"{row['required_product']}:{row['component']}"
        ]
        assert row["lineage_mapping_count"] in {1, 3}
        assert row["coverage_gap_rows"] == coverage["counts"][
            "accepted_source_coverage_gaps"
        ]
        assert row["typed_gap_membership_rows"] == coverage["counts"][
            "accepted_typed_gap_memberships"
        ]
        assert row["fee_authority_gap_rows"] == coverage["counts"]["fee_authority_gaps"]
        assert row["cross_product_intersection_count"] == 2
    # The scenario hash covers both complete rows, not only the policy time.
    both = _sha256(
        sizing.canonical_json({"policy_known_at": sizing.FEE_POLICY_KNOWN_AT})
    )
    assert descriptor["scenario_policy_sha256"] != both
    assert descriptor["configuration_sha256"] != both
    assert descriptor["future_reference_identity_allocation"]["bytes"] == (
        2 * ((68 + 9) + (67 + 9))
    )
    assert descriptor["future_partition_field_allocation"]["bytes"] > 0
    assert descriptor["cross_product_partition_intersection"] == [
        {"native_symbol": "BTCUSDT", "utc_month": "2020-01"},
        {"native_symbol": "ETHUSDT", "utc_month": "2020-02"},
    ]
    assert "partition_sha256" in descriptor["unresolved_future_fields"]


def test_zero_official_fee_rows_stay_distinct_from_the_fee_gaps(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    receipt = _run(accepted, tmp_path)["receipt"]
    fee = receipt["fee_authority"]
    coverage = receipt["coverage_authority"]
    components = receipt["cost_calibration_components"]
    # Three structurally distinct facts: zero official rows, N gaps, two policy rows.
    assert fee["official_historical_rows"] == 0
    assert fee["official_component_schema"]
    assert coverage["fee_authority_gaps"] == len(accepted["accepted_membership"])
    assert len(fee["scenario_policy_rows"]) == 2
    assert components["official_fee_schedule"]["projected_rows"] == 0
    assert components["official_fee_schedule"]["projected_bytes"] > 0
    assert components["fee_authority_gap"]["projected_rows"] == (
        coverage["fee_authority_gaps"]
    )
    assert components["scenario_policy"]["projected_rows"] == 2
    # The five components each carry their own schema.
    for component in sizing.COST_COMPONENTS:
        assert components[component]["schema"]
        assert components[component]["catalog_pages"] == components[component][
            "partition_count"
        ]
    assert components["projected_bytes"] == sum(
        components[name]["projected_bytes"] for name in sizing.COST_COMPONENTS
    )
    assert coverage["typed_gap_membership_component"]["projected_rows"] == (
        coverage["accepted_typed_gap_memberships"]
    )
    assert coverage["source_gap_component"]["projected_rows"] == (
        coverage["accepted_source_coverage_gaps"]
    )
    assert coverage["quality_gap_component"]["projected_rows"] == coverage[
        "projected_quality_gap_rows"
    ]


def test_the_coverage_authority_starts_from_the_full_accepted_matrix(
    accepted: dict[str, Any],
) -> None:
    report = json.loads(accepted["files"]["report"].read_text())
    coverage = sizing.prove_coverage_authority(report)
    counts = coverage["counts"]
    matrix = accepted["matrix_rows"]
    assert counts["accepted_source_coverage_gaps"] == sum(
        len(row["universe_coverage_gaps"]) for row in matrix
    )
    assert counts["accepted_typed_gap_memberships"] == sum(
        len(row["typed_gap_symbols"]) for row in matrix
    )
    # Fee gaps are one per accepted membership identity, and are a separate count.
    # The fixture's complete accepted membership governs, never a stale literal.
    assert counts["fee_authority_gaps"] == len(accepted["accepted_membership"])
    assert counts["known_coverage_rows"] == (
        counts["accepted_source_coverage_gaps"] + counts["fee_authority_gaps"]
    )
    assert counts["accepted_typed_gap_memberships"] != counts["known_coverage_rows"]
    # Coverage is not inferred from the Coinalyze non-mappings.
    assert counts["accepted_source_coverage_gaps"] != len(accepted["unmapped"])
    assert counts["official_historical_fee_rows"] == 0
    assert counts["fee_scenario_policy_rows"] == 2
    assert {item["gap_kind"] for item in coverage["fee_gaps"]} == {
        "historical_fee_schedule_unavailable"
    }


def test_the_pinned_coverage_minimum_is_8317_3742_771_and_9088() -> None:
    assert sizing.ACCEPTED_SOURCE_COVERAGE_GAPS == 8_317
    assert sizing.ACCEPTED_TYPED_GAP_MEMBERSHIPS == 3_742
    assert sizing.ACCEPTED_FEE_AUTHORITY_GAPS == 771
    assert sizing.ACCEPTED_MEMBERSHIP_IDENTITIES == 771
    assert sizing.ACCEPTED_KNOWN_COVERAGE_ROWS == 9_088
    assert (
        sizing.ACCEPTED_SOURCE_COVERAGE_GAPS + sizing.ACCEPTED_FEE_AUTHORITY_GAPS
        == sizing.ACCEPTED_KNOWN_COVERAGE_ROWS
    )
    # The typed-gap memberships are a separate proved count, not a substitute.
    assert sizing.ACCEPTED_TYPED_GAP_MEMBERSHIPS != sizing.ACCEPTED_KNOWN_COVERAGE_ROWS


@pytest.mark.parametrize(
    ("expected_rows", "reserved"), [(0, 0), (1, 1), (2, 1), (3, 2), (288, 144), (287, 144)]
)
def test_the_quality_gap_ceiling_is_half_the_expected_grid(
    expected_rows: int, reserved: int
) -> None:
    assert sizing.quality_gap_reservation(expected_rows) == reserved


def test_no_backdated_fee_row_and_exactly_two_policy_scenarios() -> None:
    rows = sizing.fee_scenario_rows()
    assert len(rows) == 2
    assert sizing.ACCEPTED_OFFICIAL_FEE_ROWS == 0
    ids = [row["scenario_id"] for row in rows]
    assert ids == [
        "assumed_conservative_5bps_per_side_v1",
        "assumed_severe_10bps_per_side_v1",
    ]
    for row in rows:
        assert row["authority_class"] == "ASSUMED_CONSERVATIVE"
        assert row["policy_known_at"] == "2026-08-23T03:00:00Z"
        assert row["charges_each_side"] is True
        # No maker credit, rebate, discount, or referral is ever enabled.
        assert row["maker_credit_enabled"] is False
        assert row["rebates_enabled"] is False
        assert row["vip_discounts_enabled"] is False
        assert row["referral_discounts_enabled"] is False
        assert row["bnb_discount_enabled"] is False
        assert row["scope"] == "binance_usdm_perpetual_execution"
    assert rows[0]["maker_rate"] == Decimal("0.0005")
    assert rows[0]["taker_rate"] == Decimal("0.0005")
    assert rows[1]["maker_rate"] == Decimal("0.0010")
    assert rows[1]["taker_rate"] == Decimal("0.0010")
    # The severe row is exactly twice the primary one, and neither is zero.
    assert rows[1]["taker_rate"] == rows[0]["taker_rate"] * 2
    assert all(row["taker_rate"] > 0 for row in rows)
    # The policy time is after every historical decision in the release.
    assert sizing.FEE_POLICY_KNOWN_AT > "2026-01-01T00:00:00Z"
    source = Path(sizing.__file__).read_text(encoding="utf-8")
    assert "ref_fee_schedule" not in source
    assert "known_from" not in source


def test_the_coinalyze_projection_applies_each_coefficient_once(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    """Finding 7: no raw-byte factor may be multiplied into the typed coefficient."""
    resolved = _coinalyze(accepted)
    model = _lineage_model(payload=1, footer=2, framing=12)
    projection = project_coinalyze(
        evidence=resolved["evidence"],
        supported=resolved["supported"],
        unmapped=resolved["unmapped"],
        lifecycles=resolved["lifecycles"],
        identities=resolved["identities"],
        lineage=model,
        staging=tmp_path,
    )
    block = projection.to_dict()
    per_point = min(int(item["bytes_per_point"]) for item in projection.envelopes)
    best = max(int(item["bytes_per_point"]) for item in projection.envelopes)
    assert per_point > 0
    # Typed payload is the projected point count times the typed per-point coefficient,
    # with the raw point charge appearing only in the raw projection.
    assert block["projected_typed_payload_bytes"] == (
        projection.projected_points * best
    )
    assert block["projected_typed_payload_bytes"] != (
        projection.projected_points * projection.point_charge_bytes * best
    )
    assert block["gross_liquidation_bytes"] == (
        projection.projected_points * projection.point_charge_bytes
        + projection.liquidation_receipts * projection.framing_charge_bytes
    )
    # Payload, overhead, lineage, and mapping counts are published separately.
    assert block["projected_normalized_bytes"] == (
        block["projected_typed_payload_bytes"]
        + block["projected_typed_overhead_bytes"]
        + block["projected_partition_manifest_bytes"]
    )
    assert block["partition_manifest_mappings"] == projection.partition_count
    assert block["largest_partition_bytes"] > 0


def test_real_lineage_is_bound_and_unknowns_stay_unknown(
    accepted: dict[str, Any],
) -> None:
    """The checkpoint's own `retrieval_time` and the report's availability semantics."""
    authority = load_sizing_authority(accepted["paths"])
    cohort = derive_sample_cohort(authority)
    checkpoint = dict(authority.progress_checkpoint["objects"])
    lineage = bind_sample_lineage(
        authority.report, checkpoint=checkpoint, cohort=cohort
    )
    bound = dict(lineage["bindings"])
    assert set(bound) == {item.key for item in cohort}
    known = [item for item in bound.values() if item["retrieval_time_known"]]
    unknown = [item for item in bound.values() if not item["retrieval_time_known"]]
    assert known and unknown
    for item in known:
        assert item["retrieval_time"] == "2026-08-21T00:00:00+00:00"
    for item in unknown:
        # Unknown stays unknown: no invented string, no checkpoint status stand-in.
        assert item["retrieval_time"] is None
        assert item["retrieval_time"] != "checkpoint_complete"
    for item in bound.values():
        # Availability semantics come from the report, not from checkpoint completion.
        assert item["availability_semantics"] == "source_object_listing_time_unknown"
        assert item["availability_semantics"] != item["checkpoint_status"]
        assert item["checkpoint_status"] == "complete"
        assert item["source_available_at"] is None


@pytest.mark.parametrize(
    ("damage", "message"),
    [
        ("missing_record", "no accepted report sample record"),
        # An additional identical alias is legitimately folded by the binder; the
        # accepted 106/96/10 decomposition is the authority that rejects it.
        ("duplicate_record", "lineage.logical_records"),
        ("substituted_digest", "report_sample.sha256"),
        ("substituted_size", "report_sample.byte_size"),
        ("substituted_family", "report_sample.family"),
        ("missing_semantics", "no availability semantics"),
        ("conflicting_retrieval", "retrieval_time"),
    ],
)
def test_damaged_lineage_bindings_block(
    accepted: dict[str, Any], damage: str, message: str
) -> None:
    authority = load_sizing_authority(accepted["paths"])
    cohort = derive_sample_cohort(authority)
    checkpoint = dict(authority.progress_checkpoint["objects"])
    report = json.loads(accepted["files"]["report"].read_text())
    keys = {item.key for item in cohort}
    records = [dict(item) for item in report["samples"]]
    record_count: dict[str, int] = {}
    for item in records:
        record_count[str(item["key"])] = record_count.get(str(item["key"]), 0) + 1
    # A cohort key carrying exactly one report sample record. A key that legitimately
    # appears in two sample regimes would disagree with its own alias first, so the
    # intended checkpoint mismatch would never be reached.
    target = next(
        item
        for item in records
        if item["key"] in keys and record_count[str(item["key"])] == 1
    )
    assert target["key"] not in accepted["alias_keys"]
    if damage == "missing_record":
        records = [item for item in records if item["key"] != target["key"]]
    elif damage == "duplicate_record":
        records.append(dict(target))
    elif damage == "substituted_digest":
        target["sha256"] = "0" * 64
    elif damage == "substituted_size":
        target["byte_size"] = int(target["byte_size"]) + 1
    elif damage == "substituted_family":
        target["family"] = next(
            family for family in PHYSICAL_FAMILIES if family != target["family"]
        )
    elif damage == "missing_semantics":
        target["availability_semantics"] = ""
    else:
        checkpoint = dict(checkpoint)
        entry = dict(checkpoint[target["key"]])
        entry["retrieval_time"] = "2026-08-22T00:00:00+00:00"
        target["retrieval_time"] = "2026-08-21T00:00:00+00:00"
        checkpoint[target["key"]] = entry
    report["samples"] = records
    if damage == "duplicate_record":
        # The binder folds the identical alias; the pinned decomposition blocks the
        # extra logical record before anything is measured or published.
        lineage = bind_sample_lineage(report, checkpoint=checkpoint, cohort=cohort)
        with pytest.raises(SizingError, match=message):
            sizing.prove_accepted_lineage_decomposition(lineage["decomposition"])
        return
    with pytest.raises(SizingError, match=message):
        bind_sample_lineage(report, checkpoint=checkpoint, cohort=cohort)


def test_version_one_evidence_is_never_read_or_rewritten(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    store = accepted["paths"].store_root
    v1_root = store / sizing.V1_SIZING_EVIDENCE_ROOT
    v1_root.mkdir(parents=True)
    frozen = v1_root / "keep.parquet"
    frozen.write_bytes(b"immutable version one evidence")
    before = frozen.read_bytes()
    v1_receipt = tmp_path / "180_CEX002_GATE2_STORAGE_SIZING.json"
    v1_receipt.write_bytes(b'{"schema_version": "cex002_gate2_storage_sizing_v1"}\n')
    _run(accepted, tmp_path)
    # The v1 tree and receipt are byte-identical, and v2 wrote its own root only.
    assert frozen.read_bytes() == before
    assert list(v1_root.iterdir()) == [frozen]
    assert v1_receipt.read_bytes().startswith(b'{"schema_version"')
    assert (store / sizing.SIZING_EVIDENCE_ROOT).is_dir()
    # Targeting the accepted v1 receipt path is refused outright.
    with pytest.raises(SizingError, match="never rewrite the accepted version-1"):
        _run(accepted, tmp_path, receipt_path=v1_receipt)


def test_v2_envelopes_are_content_addressed_and_reused_not_rewritten(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    first = _run(accepted, tmp_path)
    root = accepted["paths"].store_root / sizing.SIZING_EVIDENCE_ROOT
    envelopes = sorted(path.name for path in root.glob("*.parquet"))
    assert envelopes
    assert all(name.split(".")[0] == _sha256((root / name).read_bytes()) for name in envelopes)
    digests = {name: _sha256((root / name).read_bytes()) for name in envelopes}
    second = _run(accepted, tmp_path)
    assert second["publication"]["rerun"] is True
    assert second["publication"]["envelopes_published"] == 0
    assert second["publication"]["envelopes_reused"] == (
        first["publication"]["envelopes_published"]
    )
    assert {
        name: _sha256((root / name).read_bytes())
        for name in sorted(path.name for path in root.glob("*.parquet"))
    } == digests


@pytest.mark.parametrize("available", ["ample", "starved"])
def test_the_blocked_and_sufficient_boundary_is_exact(
    accepted: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    available: str,
) -> None:
    """Sufficient exactly when the exact sum is no greater than available bytes."""
    calls = {"n": 0}
    ample = 1 << 60

    def _available(_path: Path) -> int:
        calls["n"] += 1
        if available == "ample":
            return ample
        # The pre-write observation feeds the reserve; the second is the availability
        # the exact component sum is compared against.
        return ample if calls["n"] == 1 else 1 << 20

    monkeypatch.setattr(sizing, "measure_available_bytes", _available)
    receipt = _run(accepted, tmp_path)["receipt"]
    capacity = receipt["capacity"]
    total = capacity["total_future_storage_bytes"]
    post = receipt["filesystem"]["post_publication_available_bytes"]
    # The published numbers decide the state; the boundary is `<=`, never a margin.
    if total <= post:
        assert receipt["storage_preflight_state"] == STATE_SUFFICIENT
        assert receipt["blockers"] == []
        assert "authorizes no acquisition" in receipt["authorization"]
    else:
        assert receipt["storage_preflight_state"] == STATE_BLOCKED
        assert "available_capacity_insufficient" in receipt["blockers"]
    if available == "starved":
        assert total > post
    else:
        assert total <= post
    # Every component is a known non-negative integer, so nothing is unknown.
    for name in (
        "new_binance_raw_bytes",
        "new_coinalyze_raw_bytes",
        "typed_normalized_partition_bytes",
        "catalog_manifest_bundle_bytes",
        "bounded_temporary_work_bytes",
        "operating_reserve_bytes",
    ):
        value = capacity[name]
        assert isinstance(value, int) and not isinstance(value, bool) and value >= 0
    assert "component_unknown_or_non_integer" not in receipt["blockers"]
    assert "typed_normalization_incomplete" not in receipt["blockers"]


def test_the_stable_receipt_projection_is_the_only_reuse_boundary(
    accepted: dict[str, Any], tmp_path: Path
) -> None:
    """One explicit boundary decides reuse, and it names the fact that changed."""
    receipt = _run(accepted, tmp_path)["receipt"]
    projection = sizing.stable_receipt_projection(receipt)
    # The projection is exactly the named stable facts, and nothing else.
    assert set(projection) == set(sizing.STABLE_RECEIPT_FIELDS) | {"capacity"}
    assert set(projection["capacity"]) == set(sizing.STABLE_CAPACITY_FIELDS)
    # Every receipt field is classified. A new field cannot silently escape comparison
    # or silently enter it.
    assert set(receipt) == (
        set(sizing.STABLE_RECEIPT_FIELDS)
        | set(sizing.VOLATILE_RECEIPT_FIELDS)
        | {"capacity"}
    )
    assert not set(sizing.STABLE_RECEIPT_FIELDS) & set(sizing.VOLATILE_RECEIPT_FIELDS)
    assert set(receipt["capacity"]) == (
        set(sizing.STABLE_CAPACITY_FIELDS) | set(sizing.VOLATILE_CAPACITY_FIELDS)
    )
    assert not set(sizing.STABLE_CAPACITY_FIELDS) & set(sizing.VOLATILE_CAPACITY_FIELDS)
    # Serialization is not a measurement difference: the structure just measured and the
    # same receipt decoded from its published bytes project identically.
    stored = json.loads((tmp_path / "231_receipt.json").read_text())
    assert sizing.stable_receipt_projection(stored) == projection
    assert sizing.stable_receipt_identity(stored) == sizing.stable_receipt_identity(
        receipt
    )
    assert sizing.stable_receipt_mismatch(stored, receipt) is None
    # Every excluded sizing-time observation and frozen derivative may change without
    # changing the boundary.
    observed = {
        **receipt,
        "generated_at": "2030-01-01T00:00:00+00:00",
        "filesystem": {**receipt["filesystem"], "pre_write_available_bytes": 1},
        "blockers": ["available_capacity_insufficient"],
        "storage_preflight_state": STATE_BLOCKED,
        "authorization": "a different observation-time sentence",
        "capacity": {
            **receipt["capacity"],
            "operating_reserve_bytes": (
                int(receipt["capacity"]["operating_reserve_bytes"]) + 1
            ),
            "total_future_storage_bytes": 0,
        },
    }
    assert sizing.stable_receipt_mismatch(observed, receipt) is None
    # Every stable fact is named by its own field when it changes.
    for name in sizing.STABLE_RECEIPT_FIELDS:
        changed = {**receipt, name: "a changed stable fact"}
        assert sizing.stable_receipt_mismatch(changed, receipt) == name
    for name in sizing.STABLE_CAPACITY_FIELDS:
        changed = {
            **receipt,
            "capacity": {**receipt["capacity"], name: "a changed stable fact"},
        }
        assert sizing.stable_receipt_mismatch(changed, receipt) == f"capacity.{name}"
    # The fixed capacity policy prose is stable, not an observation. A prior that
    # rewrites it to arbitrary canonical text is named and rejected rather than reused.
    assert "equation" in sizing.STABLE_CAPACITY_FIELDS
    assert "equation" not in sizing.VOLATILE_CAPACITY_FIELDS
    rewritten = {
        **receipt,
        "capacity": {
            **receipt["capacity"],
            "equation": "every component counted twice and with overlap",
        },
    }
    assert sizing.stable_receipt_mismatch(rewritten, receipt) == "capacity.equation"
    # The envelope count is the content-addressed evidence set, so it cannot depend on
    # whether this invocation wrote those objects or found them already published.
    root = accepted["paths"].store_root / sizing.SIZING_EVIDENCE_ROOT
    assert receipt["counts"]["sizing_envelopes"] == len(
        {path.stem for path in root.glob("*.parquet")}
    )


def test_rerun_returns_the_identical_receipt_under_changed_observations(
    accepted: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _run(accepted, tmp_path)
    target = tmp_path / "231_receipt.json"
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
    # All three facts together: the target bytes never moved, the two returned receipts
    # are the same document, and both are the document the target actually holds.
    assert target.read_bytes() == published
    assert second["receipt"] == first["receipt"]
    assert second["receipt_file"] == first["receipt_file"]
    durable = json.loads(published.decode("utf-8"))
    assert first["receipt"] == durable
    assert second["receipt"] == durable


def test_rerun_below_the_reserve_floor_also_returns_the_identical_receipt(
    accepted: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _run(accepted, tmp_path)
    published = (tmp_path / "231_receipt.json").read_bytes()
    # Above the 80 GiB threshold the reserve is one fifth of availability, so a changed
    # observation changes the derived reserve. The frozen receipt still stands.
    high = 400 * 2**30
    assert operating_reserve_bytes(high) > MINIMUM_OPERATING_RESERVE_BYTES
    monkeypatch.setattr(sizing, "measure_available_bytes", lambda path: high)
    second = _run(accepted, tmp_path)
    assert second["publication"]["rerun"] is True
    assert (tmp_path / "231_receipt.json").read_bytes() == published
    assert second["receipt"] == first["receipt"]
    durable = json.loads(published.decode("utf-8"))
    assert first["receipt"] == durable
    assert second["receipt"] == durable


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
    target = tmp_path / "231_receipt.json"
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
    target = tmp_path / "231_receipt.json"
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
    target = tmp_path / "231_receipt.json"
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
        + receipt["future_width_allocations"]["projected_source_receipts"]["bytes"]
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


def test_each_required_product_is_its_own_partition_set() -> None:
    objects = _one_object_per_family()
    projections = project_typed_partitions(
        measurements=_all_measurements(),
        objects=objects,
        lineage=_lineage_model(),
    )
    archive_products = {item.product for item in sizing.PRODUCT_CONTRIBUTIONS}
    assert {item.product for item in projections} == archive_products
    # No packaging name survives as a product name.
    assert all(item.product in REQUIRED_PRODUCTS for item in projections)
    single = ceil_div(500 * 3, 2) + 1 + 12
    bar = next(item for item in projections if item.product == "binance_usdm_bar_1h")
    flow = next(
        item for item in projections if item.product == "binance_usdm_trade_flow_1h"
    )
    # The kline family feeds two required products, each its own single file.
    assert OUTPUT_MULTIPLICITY["daily/klines"] == 2
    for item in (bar, flow):
        assert item.partition_count == 1
        assert item.largest_partition_bytes == item.projected_bytes
    cost = [
        item for item in projections if item.product == "binance_usdm_cost_calibration"
    ]
    # Ticker and depth are separate components, files, overheads, and manifests.
    assert {item.component for item in cost} == {
        "retained_book_ticker",
        "retained_book_depth",
    }
    for item in cost:
        assert item.partition_count == 1
        assert item.projected_payload_bytes == ceil_div(500 * 3, 2)
        assert item.projected_bytes == item.projected_payload_bytes + 1 + 12
    assert single > 0


def test_a_missing_product_contribution_measurement_blocks() -> None:
    objects = _one_object_per_family()
    partial = [
        _typed_measurement(item.name)
        for item in sizing.PRODUCT_CONTRIBUTIONS
        if item.name != "binance_usdm_trade_flow_1h:daily_klines"
    ]
    with pytest.raises(SizingError, match="no measured coefficient"):
        project_typed_partitions(
            measurements=partial, objects=objects, lineage=_lineage_model()
        )


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
    target = tmp_path / "231_receipt.json"
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
