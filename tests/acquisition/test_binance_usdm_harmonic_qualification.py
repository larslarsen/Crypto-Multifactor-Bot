"""CEX-002 Gate 1 — prove the review-61 and review-64 defects are closed (no network)."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import io
import json
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    AMENDMENT_LEDGER_FILENAME,
    AMENDMENT_LEDGER_ID,
    BUDGET_LEDGER_FILENAME,
    COINALYZE_ANCHOR_SYMBOLS,
    CONTRACT_METADATA_FILENAME,
    CONTRACT_SNAPSHOT_DIRNAME,
    COVERAGE_BLOCKING_GAPS,
    COVERAGE_TYPED_GAPS,
    COVERAGE_UNRESOLVED_MEMBERSHIP,
    DERIVED_PRODUCTS,
    DISCOVERY_ARCHIVE_FAMILIES,
    GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
    GATE1_MAX_NEW_OBJECT_BYTES,
    GATE1_NEW_DOWNLOAD_BUDGET_BYTES,
    GATE2_STORAGE_BLOCK,
    GATE2_STORAGE_INCIDENT_NOTE,
    HOLDOUT_BOUNDARY_FILENAME,
    INTEGRITY_CHECKSUM_PROVED,
    INTEGRITY_QUARANTINED,
    INTEGRITY_SIDECAR_ABSENT,
    INTEGRITY_SIDECAR_LISTED,
    INTERVAL_REQUIRED_FAMILIES,
    KLINE_TAKER_FLOW_FIELDS,
    KNOWN_ARCHIVE_SCHEMAS,
    LEDGER_NO_TRANSFER,
    LEDGER_TRANSFERRED,
    LEGACY_BUDGET_UNRESOLVED,
    LEGACY_PLAN_BACKUP_FILENAME,
    MANIFEST_DAILY_FALLBACK,
    MANIFEST_INTEGRITY_MISSING,
    MANIFEST_MONTHLY_REJECTED,
    MANIFEST_OVERLAP,
    MEMBERSHIP_CONFIRMED,
    MEMBERSHIP_DATED_DELIVERY,
    MEMBERSHIP_DELIVERY,
    MEMBERSHIP_FAMILY_PREFIXES,
    MEMBERSHIP_SETTLEMENT_ARTIFACT,
    MEMBERSHIP_TRADIFI,
    MEMBERSHIP_UNRESOLVED,
    MEMBERSHIP_UNSUPPORTED_SEMANTICS,
    OFFICIAL_ARCHIVE_FAMILIES,
    OFFICIAL_INCREMENTAL_ENDPOINTS,
    PLAN_INPUTS_CHANGED,
    REQUIRED_PRODUCTS,
    SAMPLE_PLAN_LOCK_FILENAME,
    SEMANTICS_INCOHERENT_IDENTITY,
    SEMANTICS_SUPPORTED,
    SEMANTICS_UNKNOWN_STATUS,
    SEMANTICS_UNKNOWN_UNDERLYING,
    SOURCE_PRODUCTS,
    SOURCE_STATE_MEMBERSHIP,
    SOURCE_STATE_OFFICIAL,
    SOURCE_STATE_SAMPLE_PENDING,
    SOURCE_STATE_SECONDARY,
    SOURCE_STATE_TYPED_GAPS,
    VALIDATION_PENDING,
    VALIDATION_PROVED,
    VISION_S3_ENDPOINT,
    BudgetLedger,
    CoinalyzeClient,
    CoinalyzeResponse,
    ExchangeInfoResponse,
    HoldoutBoundary,
    ListingCheckpointStore,
    ListingObject,
    MemoryCoinalyzeTransport,
    MemoryCurrentContractSource,
    MemoryObjectIndex,
    OfficialContractMetadataStore,
    PlanInputs,
    ProductMatrixRow,
    QualificationReport,
    ResumeIntegrityError,
    RetainedChecksumIndex,
    RetryJournal,
    RetryPolicy,
    RetryRunner,
    SampleCheckpointStore,
    SamplePlan,
    SamplePlanEntry,
    SamplePlanLock,
    SourceQualificationError,
    TransportObjectIndex,
    _assert_no_overlapping_coverage,
    accept_qualification,
    build_acquisition_manifest,
    build_amendment_allowance,
    build_candidate_plan_v3,
    build_family_inventory,
    build_sample_plan,
    candidate_envelope_digest,
    candidate_preflight,
    canonical_contract_row,
    classify_membership,
    coinalyze_perp_symbol,
    contract_close_ms,
    contract_provenance,
    contract_semantics_state,
    exchange_info_server_time_ms,
    family_product_map,
    file_sha256,
    holdout_boundary_id,
    identity_bytes,
    infer_schema_fields,
    is_confirmed_perpetual_row,
    is_retryable_failure,
    kline_schema_supports_taker_flow,
    listing_authority_digest,
    listing_authority_manifest,
    listing_request_identity,
    listing_request_key,
    membership_evidence_digest,
    object_calendar_date,
    object_integrity_state,
    object_period,
    parse_current_perpetuals,
    parse_exchange_info_rows,
    parse_provider_checksum,
    parse_s3_list_bucket,
    plan_content_digest,
    qualification_exit_code,
    refuse_restricted_scope,
    retained_evidence_digest,
    retained_evidence_snapshot,
    run_source_qualification,
    select_cost_calibration_sample,
    select_nonoverlapping_objects,
    validate_exchange_info_response,
    validate_prior_plan_history,
    validate_sample_plan,
    verify_provider_sidecar,
    verify_retained_object,
    vision_object_url,
    vision_prefix,
    write_s3_list_bucket,
)

from source_audit.download import StreamResponse, TimeoutConfig
from source_audit.errors import ChecksumMismatchError, DownloadError, SizeLimitError

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "binance_usdm_harmonic_qualification"


def _zip_bytes(name: str, payload: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as handle:
        handle.writestr(name, payload)
    return buf.getvalue()


def _checksum_text(payload: bytes, filename: str) -> bytes:
    return f"{hashlib.sha256(payload).hexdigest()}  {filename}\n".encode()


_FIXED_ARCHIVE_TIME = (2020, 1, 1, 0, 0, 0)


def _stable_zip_bytes(name: str, payload: bytes) -> bytes:
    """Archive bytes that depend only on the inputs.

    ``ZipFile.writestr`` stamps the current local time into the member header, so two
    calls straddling a two-second boundary produce different bytes. A fixed member
    timestamp is required whenever the same synthetic object must be rebuilt across
    separate index constructions and still hash to the same content address.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as handle:
        info = zipfile.ZipInfo(name, date_time=_FIXED_ARCHIVE_TIME)
        info.compress_type = zipfile.ZIP_STORED
        handle.writestr(info, payload)
    return buf.getvalue()


def _distinct_kline_rows(seed: int) -> list[str]:
    """Deterministic, schema-valid headerless native one-hour kline rows."""
    rows = []
    for offset in range(2):
        open_time = 1577836800000 + (seed % 100000) * 3_600_000 + offset * 3_600_000
        close_time = open_time + 3_599_999
        open_price = float(7000 + seed % 5000 + offset)
        high = open_price + 10.0
        low = open_price - 10.0
        close = open_price + 1.0
        volume = 12.5 + offset
        quote_volume = round(close * volume, 4)
        taker_buy = round(volume / 2, 4)
        taker_buy_quote = round(quote_volume / 2, 4)
        rows.append(
            f"{open_time},{open_price},{high},{low},{close},{volume},{close_time},"
            f"{quote_volume},{10 + offset},{taker_buy},{taker_buy_quote},0"
        )
    return rows


def _distinct_trade_rows(seed: int) -> list[str]:
    """Deterministic, schema-valid headerless trade rows."""
    rows = []
    for offset in range(2):
        price = float(7000 + seed % 5000 + offset)
        qty = 0.5 + offset / 4
        rows.append(
            f"{seed + offset},{price},{qty},{round(price * qty, 4)},"
            f"{1577836800000 + seed % 1000000 + offset},"
            f"{'true' if offset % 2 == 0 else 'false'}"
        )
    return rows


def _distinct_object_payload(key: str) -> bytes:
    """Schema-valid archive bytes unique to one remote object key.

    Real remote objects never share bytes. Deriving the rows from the object key gives
    every synthetic object its own content address, so an object that was never downloaded
    is genuinely absent from the content-addressed store. Selected native one-hour kline
    keys get kline rows; discovery-only trade keys keep deterministic trade rows.
    """
    seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)
    if "/klines/" in key:
        return _stable_zip_bytes(
            "klines.csv", ("\n".join(_distinct_kline_rows(seed)) + "\n").encode("utf-8")
        )
    return _stable_zip_bytes(
        "trades.csv", ("\n".join(_distinct_trade_rows(seed)) + "\n").encode("utf-8")
    )


def _load_json(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _index_with_family(
    *,
    symbols: list[str],
    families: list[tuple[str, str]],
    interval_map: dict[str, list[str]] | None = None,
    payload_by_stem: dict[str, bytes] | None = None,
    payload_for_key: Callable[[str], bytes] | None = None,
    months: Sequence[str] = ("2019-09", "2022-06", "2026-01"),
    months_by_family: Mapping[str, Sequence[str]] | None = None,
    list_checksums: bool = True,
) -> MemoryObjectIndex:
    prefixes: dict[str, list[str]] = {}
    objects: dict[str, list[ListingObject]] = {}
    bodies: dict[str, bytes] = {}
    interval_map = interval_map or {}
    default_payload = _zip_bytes(
        "trades.csv",
        (FIXTURES / "headerless_trades.csv").read_bytes(),
    )
    payloads = payload_by_stem or {}
    for family, stem in families:
        fam_prefix = vision_prefix(*family.split("/"))
        prefixes[fam_prefix] = [f"{fam_prefix}{symbol}/" for symbol in symbols]
        for symbol in symbols:
            symbol_prefix = f"{fam_prefix}{symbol}/"
            intervals = interval_map.get(family, [])
            if intervals:
                prefixes[symbol_prefix] = [
                    f"{symbol_prefix}{interval}/" for interval in intervals
                ]
            family_months = (months_by_family or {}).get(family, months)
            targets: list[tuple[str, str]] = []
            if intervals:
                for interval in intervals:
                    interval_prefix = f"{symbol_prefix}{interval}/"
                    for month in family_months:
                        key = f"{interval_prefix}{symbol}-{stem}-{month}.zip"
                        targets.append((key, interval_prefix))
            else:
                for month in family_months:
                    key = f"{symbol_prefix}{symbol}-{stem}-{month}.zip"
                    targets.append((key, symbol_prefix))
            checksum_listings: list[tuple[str, ListingObject]] = []
            for key, object_prefix in targets:
                if payload_for_key is not None:
                    payload = payload_for_key(key)
                else:
                    payload = payloads.get(stem, default_payload)
                listing = ListingObject(key=key, size=len(payload))
                objects.setdefault(object_prefix, []).append(listing)
                url = vision_object_url(key)
                bodies[url] = payload
                checksum_body = _checksum_text(payload, key.rsplit("/", 1)[-1])
                bodies[vision_object_url(f"{key}.CHECKSUM")] = checksum_body
                checksum_listings.append(
                    (
                        object_prefix,
                        ListingObject(key=f"{key}.CHECKSUM", size=len(checksum_body)),
                    )
                )
            if list_checksums:
                # The real archive lists the ``.CHECKSUM`` sibling next to each object;
                # manifest integrity qualification depends on seeing it.
                for object_prefix, listing in checksum_listings:
                    objects.setdefault(object_prefix, []).append(listing)
    return MemoryObjectIndex(prefixes=prefixes, objects=objects, bodies=bodies)


COINALYZE_FIXTURE_FILES: dict[str, str] = {
    "/future-markets": "coinalyze_future_markets.json",
    "/liquidation-history": "coinalyze_liquidation_history.json",
    "/open-interest-history": "coinalyze_open_interest_history.json",
    "/funding-rate-history": "coinalyze_funding_rate_history.json",
    "/ohlcv-history": "coinalyze_ohlcv_history.json",
}

# Both declared anchors answer in these fixtures, which is what a real Gate 1
# qualification requires; the single-symbol set above still proves the request guards.
COINALYZE_ANCHOR_FIXTURE_FILES: dict[str, str] = {
    "/future-markets": "coinalyze_future_markets.json",
    "/liquidation-history": "coinalyze_liquidation_history_anchors.json",
    "/open-interest-history": "coinalyze_open_interest_history_anchors.json",
    "/funding-rate-history": "coinalyze_funding_rate_history_anchors.json",
    "/ohlcv-history": "coinalyze_ohlcv_history_anchors.json",
}


def _coinalyze_transport() -> MemoryCoinalyzeTransport:
    return MemoryCoinalyzeTransport.from_files(
        {path: FIXTURES / name for path, name in COINALYZE_FIXTURE_FILES.items()}
    )


def _coinalyze_anchor_transport() -> MemoryCoinalyzeTransport:
    return MemoryCoinalyzeTransport.from_files(
        {path: FIXTURES / name for path, name in COINALYZE_ANCHOR_FIXTURE_FILES.items()}
    )


# One explicit timezone-aware instant for the first qualification of every independently
# created store being compared. Each store pins its own prospective holdout boundary at its
# first authenticated instant, which is a real semantic difference between roots, so an
# identity comparison across roots must fix that instant rather than drop the field.
FIXED_QUALIFICATION_INSTANT = datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC)


# Contiguous months: a real archive has no interior month gap, and a synthetic index that
# skips years would look like one.
CONTIGUOUS_MONTHS: tuple[str, ...] = ("2020-01", "2020-02", "2020-03")


# Binance stamps this far-future delivery date on contracts that never deliver.
PERPETUAL_SENTINEL_MS: int = 4_133_404_800_000
# 2019-09-01T00:00:00Z, the earliest month the synthetic archives use.
DEFAULT_ONBOARD_MS: int = 1_567_296_000_000


def _perpetual_row(
    symbol: str,
    *,
    onboard_ms: int = DEFAULT_ONBOARD_MS,
    delivery_ms: int = PERPETUAL_SENTINEL_MS,
    status: str = "TRADING",
) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "pair": symbol,
        "contractType": "PERPETUAL",
        "status": status,
        "underlyingType": "COIN",
        "baseAsset": symbol.replace("USDT", ""),
        "quoteAsset": "USDT",
        "marginAsset": "USDT",
        "onboardDate": onboard_ms,
        "deliveryDate": delivery_ms,
    }


def _exchange_info(*symbols: str, extra: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """Authenticated current contract payload declaring exactly these perpetuals."""
    return {
        "timezone": "UTC",
        "serverTime": 1577836800000,
        "symbols": [
            *[_perpetual_row(symbol) for symbol in symbols],
            *[dict(item) for item in extra],
        ],
    }


def _contracts(
    *symbols: str, extra: Sequence[Mapping[str, Any]] = ()
) -> MemoryCurrentContractSource:
    return MemoryCurrentContractSource(_exchange_info(*symbols, extra=extra))


def _row(product: str, report: QualificationReport) -> ProductMatrixRow:
    return next(item for item in report.product_matrix if item.product == product)


def test_refuse_fixed_n_and_current_listing_scope() -> None:
    with pytest.raises(SourceQualificationError, match="fixed-N"):
        refuse_restricted_scope(
            max_symbols=20, current_listing_only=False, symbol_allowlist=None
        )
    with pytest.raises(SourceQualificationError, match="current-listing"):
        refuse_restricted_scope(
            max_symbols=None, current_listing_only=True, symbol_allowlist=None
        )
    with pytest.raises(SourceQualificationError, match="hand-selected"):
        refuse_restricted_scope(
            max_symbols=None,
            current_listing_only=False,
            symbol_allowlist=("BTCUSDT", "ETHUSDT"),
        )


def test_headerless_zip_uses_known_schema_not_numeric_first_row() -> None:
    payload = _zip_bytes("BTCUSDT-trades-2020-01.csv", (FIXTURES / "headerless_trades.csv").read_bytes())
    identity = infer_schema_fields(payload, name="BTCUSDT-trades-2020-01.zip")
    assert identity.kind == "headerless"
    assert identity.fields[0] == "id"
    assert "7000.0" not in identity.fields
    assert "1" not in identity.fields


def test_headerless_metrics_row_is_not_treated_as_a_header() -> None:
    raw = (FIXTURES / "headerless_metrics.csv").read_bytes()
    identity = infer_schema_fields(raw, name="BTCUSDT-metrics-2020-01.csv")
    assert identity.kind == "headerless"
    assert identity.fields[0] == "create_time"
    assert "BTCUSDT" not in identity.fields
    assert "1577836800000" not in identity.fields
    zipped = _zip_bytes("BTCUSDT-metrics-2020-01.csv", raw)
    zipped_identity = infer_schema_fields(zipped, name="BTCUSDT-metrics-2020-01.zip")
    assert zipped_identity.kind == "headerless"
    assert zipped_identity.fields == identity.fields


def test_headed_funding_zip_keeps_real_header() -> None:
    payload = _zip_bytes(
        "BTCUSDT-fundingRate-2020-01.csv",
        (FIXTURES / "headed_funding.csv").read_bytes(),
    )
    identity = infer_schema_fields(payload, name="BTCUSDT-fundingRate-2020-01.zip")
    assert identity.kind == "headed"
    assert identity.fields == ("calc_time", "funding_interval_hours", "last_funding_rate")


def test_resume_refuses_tampered_content_addressed_bytes(tmp_path: Path) -> None:
    # A selected, checksum-listed native one-hour kline object: trades are discovery-only
    # and are never acquired, so they cannot carry this contract.
    index = _trades_index(["BTCUSDT"])
    first = run_source_qualification(store_root=tmp_path, index=index)
    assert first.samples
    sample = next(item for item in first.samples if "/klines/" in item.key)
    Path(sample.content_path).write_bytes(b"tampered")
    with pytest.raises(SourceQualificationError, match="resume hash mismatch"):
        run_source_qualification(store_root=tmp_path, index=index)


def test_coinalyze_client_uses_real_history_endpoints_and_header_key() -> None:
    transport = _coinalyze_transport()
    client = CoinalyzeClient(transport, api_key="sekret")
    evidence = client.qualify_binance_daily(
        anchor_symbols=["BTCUSDT"],
        from_ts=1_577_836_800,
        to_ts=1_609_459_200,
    )
    assert transport.last_headers == {"api_key": "sekret"}
    assert "api_key" not in transport.last_params
    assert transport.last_params["interval"] == "daily"
    assert transport.last_params["symbols"] == "BTCUSDT_PERP.A"
    assert evidence["samples"]["liquidation"][0]["points"] == 2
    assert evidence["overlap_reconciliation"]["required_before_accepting_liquidation"] is True
    assert "daily observations are not deleted" in evidence["retention"]
    assert evidence["units"]["denominated_in"] == "BASE_ASSET"
    assert evidence["units"]["denominated_in_by_symbol"]["BTCUSDT_PERP.A"] == "BASE_ASSET"
    assert evidence["matched_markets"] == ["BTCUSDT_PERP.A"]
    assert len(evidence["provenance"]) == 5
    for item in evidence["provenance"]:
        assert len(item["sha256"]) == 64
        assert item["byte_size"] > 0
        assert "api_key" not in item["params"]
        assert "sekret" not in json.dumps(item)
    assert "sekret" not in json.dumps(evidence)


def test_cli_source_has_no_api_key_argument() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "research"
        / "qualify_binance_usdm_harmonic_sources.py"
    )
    tree = ast.parse(script.read_text(encoding="utf-8"))
    flags: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "help":
                    continue
            if isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        flags.append(arg.value)
    assert "--coinalyze-api-key" not in flags
    assert "--licensed-quotes-json" not in flags
    assert "--max-sample-object-bytes" not in flags
    text = script.read_text(encoding="utf-8")
    assert "COINALYZE_API_KEY" in text
    assert "os.environ.get(\"COINALYZE_API_KEY\")" in text


def test_s3_list_objects_v2_required_and_v1_marker_refused() -> None:
    xml = write_s3_list_bucket(
        prefixes=["data/futures/um/monthly/trades/BTCUSDT/"],
        objects=[
            ListingObject(
                key="data/futures/um/monthly/trades/BTCUSDT/BTCUSDT-trades-2020-01.zip",
                size=12,
            )
        ],
        truncated=True,
        next_marker="page-2",
    )
    with pytest.raises(SourceQualificationError, match="not ListObjectsV2"):
        parse_s3_list_bucket(xml)
    ok = write_s3_list_bucket(
        prefixes=["data/futures/um/monthly/trades/BTCUSDT/"],
        objects=[
            ListingObject(
                key="data/futures/um/monthly/trades/BTCUSDT/BTCUSDT-trades-2020-01.zip",
                size=12,
            )
        ],
        truncated=True,
        continuation="token-2",
    )
    prefixes, objects, truncated, token = parse_s3_list_bucket(ok)
    assert prefixes == ["data/futures/um/monthly/trades/BTCUSDT/"]
    assert objects[0].size == 12
    assert truncated is True
    assert token == "token-2"


def test_transport_sends_list_type_2_and_continuation_token(tmp_path: Path) -> None:
    seen: list[dict[str, list[str]]] = []
    page1 = write_s3_list_bucket(
        prefixes=["data/futures/um/monthly/trades/BTCUSDT/"],
        truncated=True,
        continuation="tok-2",
    ).encode()
    page2 = write_s3_list_bucket(
        prefixes=["data/futures/um/monthly/trades/ETHUSDT/"],
        truncated=False,
    ).encode()

    class _PagingTransport:
        def stream_get(self, url: str, *, headers, timeout: TimeoutConfig) -> StreamResponse:
            query = parse_qs(urlparse(url).query)
            seen.append(query)
            body = page2 if query.get("continuation-token") == ["tok-2"] else page1

            def _iter():
                yield body

            return StreamResponse(status_code=200, headers={}, iter_bytes=_iter(), close=lambda: None)

    index = TransportObjectIndex(
        _PagingTransport(),
        list_cache_dir=tmp_path,
    )
    prefixes = index.list_common_prefixes("data/futures/um/monthly/trades/")
    assert seen[0]["list-type"] == ["2"]
    assert "continuation-token" not in seen[0]
    assert seen[1]["continuation-token"] == ["tok-2"]
    assert seen[1]["list-type"] == ["2"]
    assert prefixes == [
        "data/futures/um/monthly/trades/BTCUSDT/",
        "data/futures/um/monthly/trades/ETHUSDT/",
    ]


def test_bar_1h_counts_only_one_hour_interval(tmp_path: Path) -> None:
    kline_zip = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h"), ("monthly/trades", "trades")],
        interval_map={"monthly/klines": ["1h", "1m"]},
        payload_by_stem={"1h": kline_zip, "trades": _zip_bytes("t.csv", (FIXTURES / "headerless_trades.csv").read_bytes())},
    )
    report = run_source_qualification(store_root=tmp_path, index=index)
    bars = next(row for row in report.product_matrix if row.product == "binance_usdm_bar_1h")
    assert bars.listed_object_count == 3
    assert all("/1m/" not in sample.key for sample in report.samples if sample.product == "binance_usdm_bar_1h")
    assert any("/1h/" in sample.key for sample in report.samples if sample.product == "binance_usdm_bar_1h")


def test_empty_listed_symbol_prefix_blocks_official_complete(tmp_path: Path) -> None:
    kline_zip = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h")],
        interval_map={"monthly/klines": ["1h"]},
        payload_by_stem={"1h": kline_zip},
    )
    kline_prefix = vision_prefix("monthly", "klines")
    index.prefixes[kline_prefix] = sorted(
        [*index.prefixes[kline_prefix], f"{kline_prefix}ETHUSDT/"]
    )
    index.objects[f"{kline_prefix}ETHUSDT/"] = []
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT", "ETHUSDT")
    )
    bars = _row("binance_usdm_bar_1h", report)
    assert bars.discovered_symbols == 2
    assert bars.official_complete is False
    assert bars.release_blocked is True
    # A listed prefix with no objects is a coverage fact, not a loss of source authority.
    assert bars.coverage_state == COVERAGE_BLOCKING_GAPS
    assert "ETHUSDT" in bars.uncovered_listed_symbols
    assert "binance_usdm_bar_1h" in report.blocked_products
    coverage = report.storage["symbol_coverage"]["binance_usdm_bar_1h"]
    assert coverage["monthly/klines/ETHUSDT"] == 0


def test_absent_family_prefix_blocks_official_complete(tmp_path: Path) -> None:
    # ETHUSDT is in the discovered archive union but has no 1h kline prefix at all.
    index = _index_with_family(
        symbols=["BTCUSDT", "ETHUSDT"],
        families=[("monthly/trades", "trades")],
    )
    kline_prefix = vision_prefix("monthly", "klines")
    kline_zip = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index.prefixes[kline_prefix] = [f"{kline_prefix}BTCUSDT/"]
    symbol_prefix = f"{kline_prefix}BTCUSDT/"
    interval_prefix = f"{symbol_prefix}1h/"
    index.prefixes[symbol_prefix] = [interval_prefix]
    index.objects[interval_prefix] = []
    for month in ("2019-09", "2022-06", "2026-01"):
        key = f"{interval_prefix}BTCUSDT-1h-{month}.zip"
        index.objects[interval_prefix].append(ListingObject(key=key, size=len(kline_zip)))
        index.bodies[vision_object_url(key)] = kline_zip
        index.bodies[vision_object_url(f"{key}.CHECKSUM")] = _checksum_text(
            kline_zip, key.rsplit("/", 1)[-1]
        )

    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT", "ETHUSDT")
    )
    assert set(report.discovered_symbols) == {"BTCUSDT", "ETHUSDT"}
    bars = _row("binance_usdm_bar_1h", report)
    assert bars.official_complete is False
    assert bars.release_blocked is True
    assert bars.coverage_state == COVERAGE_BLOCKING_GAPS
    assert "ETHUSDT" in bars.uncovered_universe_symbols
    assert "ETHUSDT" not in bars.uncovered_listed_symbols
    assert "binance_usdm_bar_1h" in report.blocked_products
    gaps = [item for item in bars.universe_coverage_gaps if item["symbol"] == "ETHUSDT"]
    assert [item["status"] for item in gaps] == ["current_unarchived"]
    assert gaps[0]["blocking"] is True
    assert gaps[0]["family_group"] == "klines"
    coverage = report.storage["symbol_coverage"]["binance_usdm_bar_1h"]
    assert coverage["monthly/klines/ETHUSDT"] == 0
    assert coverage["monthly/klines/BTCUSDT"] == 3
    assert report.storage["universe_coverage_gaps"]["binance_usdm_bar_1h"]


def test_universe_coverage_gap_is_reported_in_the_blocking_reason(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["BTCUSDT", "ETHUSDT"],
        families=[("monthly/trades", "trades")],
    )
    kline_prefix = vision_prefix("monthly", "klines")
    index.prefixes[kline_prefix] = [f"{kline_prefix}BTCUSDT/"]
    index.objects[f"{kline_prefix}BTCUSDT/"] = []
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT", "ETHUSDT")
    )
    bars = _row("binance_usdm_bar_1h", report)
    assert bars.official_complete is False
    assert "ETHUSDT" in bars.uncovered_universe_symbols
    assert "discovered universe symbols lack required family coverage" in bars.reason


def test_coinalyze_rejects_returned_symbol_mismatch() -> None:
    # ETHUSDT_PERP.A is a real market in the fixture, so the market check passes and the
    # history check is the correct rejection: only BTCUSDT_PERP.A history is returned.
    transport = _coinalyze_transport()
    client = CoinalyzeClient(transport, api_key="sekret")
    with pytest.raises(
        SourceQualificationError, match="history symbols do not match request"
    ):
        client.qualify_binance_daily(
            anchor_symbols=["ETHUSDT"],
            from_ts=1_577_836_800,
            to_ts=1_609_459_200,
        )


def test_coinalyze_rejects_symbol_absent_from_future_markets() -> None:
    transport = _coinalyze_transport()
    client = CoinalyzeClient(transport, api_key="sekret")
    with pytest.raises(SourceQualificationError, match="missing requested symbols"):
        client.qualify_binance_daily(
            anchor_symbols=["SOLUSDT"],
            from_ts=1_577_836_800,
            to_ts=1_609_459_200,
        )


def test_coinalyze_provenance_hashes_retained_raw_response_bytes() -> None:
    transport = _coinalyze_transport()
    client = CoinalyzeClient(transport, api_key="sekret")
    evidence = client.qualify_binance_daily(
        anchor_symbols=["BTCUSDT"],
        from_ts=1_577_836_800,
        to_ts=1_609_459_200,
    )
    by_path = {item["path"]: item for item in evidence["provenance"]}
    for path, name in COINALYZE_FIXTURE_FILES.items():
        raw = (FIXTURES / name).read_bytes()
        item = by_path[path]
        assert item["sha256"] == hashlib.sha256(raw).hexdigest()
        assert item["byte_size"] == len(raw)
        assert item["provenance_source"] == "raw_response_bytes"
    markets = by_path["/future-markets"]
    reconstructed = json.dumps(
        _load_json("coinalyze_future_markets.json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert markets["sha256"] != hashlib.sha256(reconstructed).hexdigest()
    assert markets["byte_size"] != len(reconstructed)


def test_coinalyze_refuses_transport_provenance_that_is_not_raw_bytes() -> None:
    class ForgedTransport:
        def fetch(
            self,
            path: str,
            *,
            params: Mapping[str, str],
            headers: Mapping[str, str],
        ) -> CoinalyzeResponse:
            raw = (FIXTURES / "coinalyze_future_markets.json").read_bytes()
            return CoinalyzeResponse(
                path=path,
                payload=json.loads(raw.decode("utf-8")),
                raw_bytes=raw,
                sha256="0" * 64,
                byte_size=len(raw),
                retrieved_at="1970-01-01T00:00:00+00:00",
                request_params=dict(params),
                header_names=tuple(sorted(headers)),
                source="forged",
            )

    client = CoinalyzeClient(ForgedTransport(), api_key="sekret")
    with pytest.raises(
        SourceQualificationError, match="does not match the retained raw response bytes"
    ):
        client.qualify_binance_daily(
            anchor_symbols=["BTCUSDT"],
            from_ts=1_577_836_800,
            to_ts=1_609_459_200,
        )


def test_missing_checksum_is_not_official_complete(tmp_path: Path) -> None:
    kline_zip = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h")],
        interval_map={"monthly/klines": ["1h"]},
        payload_by_stem={"1h": kline_zip},
    )
    checksum_urls = [url for url in index.bodies if url.endswith(".CHECKSUM")]
    for url in checksum_urls:
        del index.bodies[url]
    report = run_source_qualification(store_root=tmp_path, index=index)
    trades = next(row for row in report.product_matrix if row.product == "binance_usdm_bar_1h")
    assert trades.official_complete is False
    assert trades.authority != "official"
    assert "binance_usdm_bar_1h" in report.blocked_products


def test_licensed_quotes_argument_removed() -> None:
    signature = inspect.signature(run_source_qualification)
    assert "licensed_quotes" not in signature.parameters


def test_derived_products_do_not_block_source_gate(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[
            ("monthly/trades", "trades"),
            ("monthly/klines", "1h"),
            ("monthly/metrics", "metrics"),
            ("monthly/fundingRate", "fundingRate"),
            ("monthly/premiumIndexKlines", "premiumIndexKlines"),
            ("monthly/markPriceKlines", "markPriceKlines"),
            ("monthly/indexPriceKlines", "indexPriceKlines"),
            ("daily/bookTicker", "bookTicker"),
            ("daily/bookDepth", "bookDepth"),
        ],
        interval_map={
            "monthly/klines": ["1h"],
            "monthly/premiumIndexKlines": ["1h"],
            "monthly/markPriceKlines": ["1h"],
            "monthly/indexPriceKlines": ["1h"],
        },
        months=("2020-01-01", "2020-01-15", "2020-01-31"),
        payload_by_stem={
            "1h": _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes()),
            "premiumIndexKlines": _zip_bytes(
                "k.csv", (FIXTURES / "headerless_klines.csv").read_bytes()
            ),
            "markPriceKlines": _zip_bytes(
                "k.csv", (FIXTURES / "headerless_klines.csv").read_bytes()
            ),
            "indexPriceKlines": _zip_bytes(
                "k.csv", (FIXTURES / "headerless_klines.csv").read_bytes()
            ),
            "fundingRate": _zip_bytes("f.csv", (FIXTURES / "headed_funding.csv").read_bytes()),
            "metrics": _zip_bytes("m.csv", (FIXTURES / "headerless_metrics.csv").read_bytes()),
            "bookTicker": _zip_bytes(
                "b.csv", (FIXTURES / "headerless_book_ticker.csv").read_bytes()
            ),
            "bookDepth": _zip_bytes(
                "d.csv", (FIXTURES / "headerless_book_depth.csv").read_bytes()
            ),
        },
    )
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=MemoryCurrentContractSource(_load_json("exchange_info.json")),
        coinalyze_transport=_coinalyze_anchor_transport(),
        coinalyze_api_key="sekret",
    )
    assert set(DERIVED_PRODUCTS).isdisjoint(report.blocked_products)
    authorities = {row.product: row.authority for row in report.product_matrix}
    # A valid native one-hour kline schema gives the derived product official authority
    # while it still stays outside the source gate.
    assert authorities["binance_usdm_trade_flow_1h"] == "official"
    assert "binance_usdm_trade_flow_1h" in DERIVED_PRODUCTS
    assert authorities["binance_usdm_liquidation_observed_daily"] == "secondary"
    assert "binance_usdm_liquidation_observed_daily" not in report.blocked_products
    assert report.coinalyze["qualified"] is True
    assert report.current_contracts_authenticated is True
    assert "XMRUSDT" not in report.current_perpetual_symbols
    # A TradFi continuous contract is reported and excluded, never counted as a crypto
    # USD-M perpetual under ADR-0017 scope.
    assert "AAPLUSDT" not in report.current_perpetual_symbols
    assert "AAPLUSDT" in report.membership["classes"][MEMBERSHIP_TRADIFI]
    assert qualification_exit_code(report) in {0, 2}


def test_coinalyze_changes_liquidation_authority(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["BTCUSDT", "ETHUSDT"],
        families=[("monthly/trades", "trades")],
        months=CONTIGUOUS_MONTHS,
    )
    contracts = _contracts("BTCUSDT", "ETHUSDT")
    blocked = run_source_qualification(
        store_root=tmp_path / "a", index=index, current_contracts=contracts
    )
    liq_blocked = _row("binance_usdm_liquidation_observed_daily", blocked)
    assert liq_blocked.authority == "inaccessible"
    assert liq_blocked.official_complete is False
    qualified = run_source_qualification(
        store_root=tmp_path / "b",
        index=index,
        current_contracts=_contracts("BTCUSDT", "ETHUSDT"),
        coinalyze_transport=_coinalyze_anchor_transport(),
        coinalyze_api_key="sekret",
    )
    liq = _row("binance_usdm_liquidation_observed_daily", qualified)
    assert liq.authority == "secondary"
    assert liq.source_qualification_state == SOURCE_STATE_SECONDARY
    assert liq.official_complete is True
    assert "observed/censored" in liq.reason


def test_cost_calibration_requires_book_depth_and_ticker(tmp_path: Path) -> None:
    book_payloads = {
        "bookTicker": _zip_bytes(
            "b.csv", (FIXTURES / "headerless_book_ticker.csv").read_bytes()
        ),
        "bookDepth": _zip_bytes(
            "d.csv", (FIXTURES / "headerless_book_depth.csv").read_bytes()
        ),
    }
    dates = ("2020-01-01", "2020-01-15", "2020-01-31")
    ticker_only = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("daily/bookTicker", "bookTicker")],
        payload_by_stem=book_payloads,
        months=dates,
    )
    report = run_source_qualification(
        store_root=tmp_path / "t", index=ticker_only, current_contracts=_contracts("BTCUSDT")
    )
    cost = _row("binance_usdm_cost_calibration", report)
    assert cost.official_complete is False
    both = _index_with_family(
        symbols=["BTCUSDT"],
        families=[
            ("daily/bookTicker", "bookTicker"),
            ("daily/bookDepth", "bookDepth"),
        ],
        payload_by_stem=book_payloads,
        months=dates,
    )
    complete = run_source_qualification(
        store_root=tmp_path / "b", index=both, current_contracts=_contracts("BTCUSDT")
    )
    cost_both = _row("binance_usdm_cost_calibration", complete)
    assert cost_both.listed_object_count == 6
    assert cost_both.official_complete is True
    assert cost_both.authority == "official"
    assert cost_both.source_qualification_state == SOURCE_STATE_TYPED_GAPS
    assert cost_both.coverage_state == COVERAGE_TYPED_GAPS
    assert cost_both.release_blocked is False
    assert "head_gap_family_launch" in cost_both.coverage_gap_kinds


def test_authenticated_current_perpetual_rule(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["AAVEUSDT", "BTCUSDT", "ETHUSDT", "XMRUSDT"],
        families=[("monthly/trades", "trades")],
    )
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=MemoryCurrentContractSource(_load_json("exchange_info.json")),
    )
    assert report.current_contracts_authenticated is True
    assert report.current_perpetual_symbols == ("AAVEUSDT", "BTCUSDT", "ETHUSDT")
    assert "XMRUSDT" in report.historical_or_delisted_candidates
    assert "BTCUSDT_240329" not in report.current_perpetual_symbols
    assert "PERPETUAL" in report.historical_perpetual_rule


def test_exchange_info_rejects_unauthenticated_payload() -> None:
    with pytest.raises(SourceQualificationError, match="missing symbols"):
        parse_current_perpetuals({"timezone": "UTC"})


def test_default_exit_is_nonzero_when_blocked(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/trades", "trades")],
    )
    report = run_source_qualification(store_root=tmp_path, index=index)
    assert report.gate_status == "BLOCKED"
    assert qualification_exit_code(report) == 2
    with pytest.raises(SourceQualificationError, match="incomplete product matrix"):
        accept_qualification(report)


def test_identity_bytes_stable_across_resume(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT", "ETHUSDT"])
    first = run_source_qualification(store_root=tmp_path, index=index)
    second = run_source_qualification(store_root=tmp_path, index=index)
    assert second.resume["reused_samples"] > 0
    assert identity_bytes(first) == identity_bytes(second)
    assert first.generated_at != second.generated_at or first.samples[0].retrieval_time != ""


def test_empty_archive_listing_is_not_a_current_listing_universe(tmp_path: Path) -> None:
    index = MemoryObjectIndex(prefixes={vision_prefix("monthly", "trades"): []})
    with pytest.raises(SourceQualificationError, match="empty historical family"):
        run_source_qualification(store_root=tmp_path, index=index)


def test_required_source_products_are_complete_set() -> None:
    assert "binance_usdm_trade_flow_1h" in DERIVED_PRODUCTS
    assert "binance_usdm_liquidation_observed_daily" in SOURCE_PRODUCTS
    assert list(REQUIRED_PRODUCTS)[:3] == [
        "binance_usdm_perpetual_membership",
        "binance_usdm_bar_1h",
        "binance_usdm_trade_flow_1h",
    ]


def test_parse_provider_checksum() -> None:
    digest = "a" * 64
    assert parse_provider_checksum(f"{digest}  file.zip\n") == digest


# --- review-67 operational correction ------------------------------------------------


def _real_shaped_page(
    *,
    prefix: str,
    prefixes: list[str] | None = None,
    objects: list[ListingObject] | None = None,
    truncated: bool = False,
    continuation: str | None = None,
    continuation_token: str | None = None,
) -> bytes:
    return write_s3_list_bucket(
        prefixes=prefixes or [],
        objects=objects or [],
        truncated=truncated,
        continuation=continuation,
        prefix=prefix,
        delimiter="/",
        continuation_token=continuation_token,
    ).encode()


class _ScriptedTransport:
    """Serves scripted listing pages and can fail a chosen request exactly once."""

    def __init__(
        self,
        pages: dict[tuple[str, str | None], bytes],
        *,
        fail_on: tuple[str, str | None] | None = None,
        failures: int = 1,
        status: int | None = None,
    ) -> None:
        self.pages = pages
        self.fail_on = fail_on
        self.remaining_failures = failures
        self.status = status
        self.requests: list[tuple[str, str | None]] = []

    def stream_get(self, url: str, *, headers, timeout: TimeoutConfig) -> StreamResponse:
        query = parse_qs(urlparse(url).query)
        prefix = query.get("prefix", [""])[0]
        token = query.get("continuation-token", [None])[0]
        key = (prefix, token)
        self.requests.append(key)
        if self.fail_on == key and self.remaining_failures > 0:
            self.remaining_failures -= 1
            if self.status is not None:
                def _empty():
                    yield b""

                return StreamResponse(
                    status_code=self.status, headers={}, iter_bytes=_empty(), close=lambda: None
                )
            raise httpx.ConnectError("Connection reset by peer")
        body = self.pages[key]

        def _iter():
            yield body

        return StreamResponse(
            status_code=200, headers={}, iter_bytes=_iter(), close=lambda: None
        )


def _trades_pages() -> dict[tuple[str, str | None], bytes]:
    root = vision_prefix("monthly", "trades")
    btc = f"{root}BTCUSDT/"
    return {
        (root, None): _real_shaped_page(
            prefix=root, prefixes=[btc], truncated=True, continuation="tok-2"
        ),
        (root, "tok-2"): _real_shaped_page(
            prefix=root,
            prefixes=[f"{root}ETHUSDT/"],
            continuation_token="tok-2",
        ),
    }


def test_listing_checkpoint_reuses_completed_pages_after_a_reset(tmp_path: Path) -> None:
    root = vision_prefix("monthly", "trades")
    pages = _trades_pages()
    checkpoint_path = tmp_path / "listing.json"
    cache = tmp_path / "list_cache"

    failing = _ScriptedTransport(pages, fail_on=(root, "tok-2"), failures=99)
    store = ListingCheckpointStore.load(checkpoint_path, cache)
    index = TransportObjectIndex(
        failing,
        list_cache_dir=cache,
        checkpoint=store,
        retry=RetryRunner(
            policy=RetryPolicy(max_attempts=2), sleeper=lambda _d: None, jitter=lambda d: d
        ),
    )
    with pytest.raises(SourceQualificationError, match="bounded attempt limit"):
        index.list_common_prefixes(root)
    # The first page completed and is durably checkpointed even though the run aborted.
    assert len(store.entries) == 1
    assert (root, None) in failing.requests

    healthy = _ScriptedTransport(pages)
    resumed_store = ListingCheckpointStore.load(checkpoint_path, cache)
    assert len(resumed_store.entries) == 1
    resumed = TransportObjectIndex(
        healthy,
        list_cache_dir=cache,
        checkpoint=resumed_store,
        retry=RetryRunner(sleeper=lambda _d: None, jitter=lambda d: d),
    )
    prefixes = resumed.list_common_prefixes(root)
    assert prefixes == [f"{root}BTCUSDT/", f"{root}ETHUSDT/"]
    # Only the uncompleted continuation request was fetched again.
    assert healthy.requests == [(root, "tok-2")]
    assert resumed_store.reused == 1
    assert resumed_store.fetched == 1


def test_listing_checkpoint_rehashes_and_fails_closed_on_tampered_bytes(tmp_path: Path) -> None:
    root = vision_prefix("monthly", "trades")
    pages = _trades_pages()
    cache = tmp_path / "list_cache"
    store = ListingCheckpointStore.load(tmp_path / "listing.json", cache)
    index = TransportObjectIndex(
        _ScriptedTransport(pages),
        list_cache_dir=cache,
        checkpoint=store,
        retry=RetryRunner(sleeper=lambda _d: None, jitter=lambda d: d),
    )
    index.list_common_prefixes(root)
    entry = next(iter(store.entries.values()))
    Path(entry["content_path"]).write_bytes(b"tampered listing")
    reloaded = ListingCheckpointStore.load(tmp_path / "listing.json", cache)
    with pytest.raises(ResumeIntegrityError, match="listing checkpoint hash mismatch"):
        TransportObjectIndex(
            _ScriptedTransport(pages),
            list_cache_dir=cache,
            checkpoint=reloaded,
            retry=RetryRunner(sleeper=lambda _d: None, jitter=lambda d: d),
        ).list_common_prefixes(root)


def test_listing_checkpoint_bootstraps_only_provable_request_identity(tmp_path: Path) -> None:
    cache = tmp_path / "list_cache"
    cache.mkdir(parents=True)
    root = vision_prefix("monthly", "trades")
    page = _real_shaped_page(prefix=root, prefixes=[f"{root}BTCUSDT/"])
    (cache / hashlib.sha256(page).hexdigest()).write_bytes(page)
    checksum_body = b"%s  BTCUSDT-trades-2020-01.zip\n" % (b"a" * 64)
    (cache / hashlib.sha256(checksum_body).hexdigest()).write_bytes(checksum_body)
    opaque = b"<?xml version=\"1.0\"?><Other/>"
    (cache / hashlib.sha256(opaque).hexdigest()).write_bytes(opaque)

    store = ListingCheckpointStore.load(tmp_path / "listing.json", cache)
    counts = store.bootstrap(endpoint=VISION_S3_ENDPOINT)
    assert counts["claimed"] == 1
    assert counts["checksum_blobs"] == 1
    assert counts["unclaimed"] == 1
    key = listing_request_key(
        listing_request_identity(
            endpoint=VISION_S3_ENDPOINT, prefix=root, delimiter="/", continuation_token=None
        )
    )
    assert key in store.entries
    assert store.entries[key]["bootstrapped"] is True
    # A bootstrapped page is reused instead of refetched.
    transport = _ScriptedTransport({})
    index = TransportObjectIndex(
        transport,
        list_cache_dir=cache,
        checkpoint=store,
        retry=RetryRunner(sleeper=lambda _d: None, jitter=lambda d: d),
    )
    assert index.list_common_prefixes(root) == [f"{root}BTCUSDT/"]
    assert transport.requests == []


def test_retry_is_bounded_and_only_for_transient_failures() -> None:
    delays: list[float] = []
    runner = RetryRunner(
        policy=RetryPolicy(max_attempts=4, base_delay_s=1.0, max_delay_s=8.0),
        sleeper=delays.append,
        jitter=lambda d: d,
    )
    attempts = {"n": 0}

    def _flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise DownloadError("reset", context={"url": "x"})
        return "ok"

    assert runner.run("flaky", _flaky) == "ok"
    assert delays == [1.0, 2.0]
    assert runner.retries == 2

    terminal = RetryRunner(sleeper=delays.append, jitter=lambda d: d)
    with pytest.raises(ChecksumMismatchError):
        terminal.run("checksum", lambda: (_ for _ in ()).throw(ChecksumMismatchError("bad")))
    assert terminal.retries == 0

    forbidden = RetryRunner(sleeper=delays.append, jitter=lambda d: d)
    with pytest.raises(DownloadError):
        forbidden.run(
            "auth",
            lambda: (_ for _ in ()).throw(
                DownloadError("HTTP status 403", context={"status_code": 403})
            ),
        )
    assert forbidden.retries == 0


def test_retryable_classification_covers_429_5xx_and_transport() -> None:
    assert is_retryable_failure(DownloadError("reset", context={})) is True
    assert is_retryable_failure(DownloadError("429", context={"status_code": 429})) is True
    assert is_retryable_failure(DownloadError("503", context={"status_code": 503})) is True
    assert is_retryable_failure(DownloadError("404", context={"status_code": 404})) is False
    assert is_retryable_failure(DownloadError("401", context={"status_code": 401})) is False
    assert is_retryable_failure(ChecksumMismatchError("bad")) is False
    assert is_retryable_failure(SizeLimitError("too big")) is False
    assert is_retryable_failure(SourceQualificationError("schema")) is False


def test_retry_recovers_a_transient_listing_reset(tmp_path: Path) -> None:
    root = vision_prefix("monthly", "trades")
    pages = _trades_pages()
    transport = _ScriptedTransport(pages, fail_on=(root, None), failures=1)
    store = ListingCheckpointStore.load(tmp_path / "listing.json", tmp_path / "cache")
    retry = RetryRunner(
        policy=RetryPolicy(max_attempts=3), sleeper=lambda _d: None, jitter=lambda d: d
    )
    index = TransportObjectIndex(
        transport, list_cache_dir=tmp_path / "cache", checkpoint=store, retry=retry
    )
    assert index.list_common_prefixes(root) == [f"{root}BTCUSDT/", f"{root}ETHUSDT/"]
    assert retry.retries == 1
    assert retry.incidents[0]["label"] == f"list:{root}"


def test_physical_family_is_inventoried_once_for_all_products(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/trades", "trades")],
    )
    calls: list[str] = []
    original = index.list_common_prefixes

    def _counted(prefix: str) -> list[str]:
        calls.append(prefix)
        return original(prefix)

    index.list_common_prefixes = _counted  # type: ignore[method-assign]
    report = run_source_qualification(store_root=tmp_path, index=index)
    trades_prefix = vision_prefix("monthly", "trades")
    # monthly/trades belongs to both the membership and trade products but is listed once.
    assert calls.count(trades_prefix) == 1
    assert report.resume["physical_families_inventoried"] == len(MEMBERSHIP_FAMILY_PREFIXES)


def test_sample_checkpoint_is_written_per_object_not_at_end(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    progress = tmp_path / "progress.json"
    seen_counts: list[int] = []
    real_fetch = index.fetch_bytes

    def _observing(url: str) -> bytes:
        if progress.is_file():
            data = json.loads(progress.read_text())
            seen_counts.append(len(data.get("objects", {})))
        return real_fetch(url)

    index.fetch_bytes = _observing  # type: ignore[method-assign]
    report = run_source_qualification(
        store_root=tmp_path, index=index, progress_path=progress
    )
    assert report.samples
    # The checkpoint file grew while the run was still fetching, not only at the end.
    assert seen_counts and max(seen_counts) > 0
    saved = json.loads(progress.read_text())
    assert len(saved["objects"]) == len({item.key for item in report.samples})


def test_retained_samples_are_recovered_without_redownload(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    first = run_source_qualification(store_root=tmp_path, index=index)
    assert first.samples
    sample = first.samples[0]

    # Drop the sample checkpoint but keep the retained bytes and the provider checksum
    # sidecar, exactly like the interrupted real run.
    progress = tmp_path / "cex002_qualification_progress.json"
    progress.unlink()
    cache = tmp_path / "list_cache"
    cache.mkdir(parents=True, exist_ok=True)
    body = f"{sample.provider_checksum}  {sample.key.rsplit('/', 1)[-1]}\n".encode()
    (cache / hashlib.sha256(body).hexdigest()).write_bytes(body)

    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    second = run_source_qualification(store_root=tmp_path, index=index)
    assert second.resume["recovered_samples"] >= 1
    assert sample.url not in fetched
    recovered = next(item for item in second.samples if item.key == sample.key)
    assert recovered.sha256 == sample.sha256
    assert recovered.reused_existing is True


def test_recovery_fails_closed_on_tampered_retained_bytes(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    first = run_source_qualification(store_root=tmp_path, index=index)
    sample = first.samples[0]
    (tmp_path / "cex002_qualification_progress.json").unlink()
    cache = tmp_path / "list_cache"
    cache.mkdir(parents=True, exist_ok=True)
    body = f"{sample.provider_checksum}  {sample.key.rsplit('/', 1)[-1]}\n".encode()
    (cache / hashlib.sha256(body).hexdigest()).write_bytes(body)
    Path(sample.content_path).write_bytes(b"tampered")
    with pytest.raises(ResumeIntegrityError, match="do not match the retained provider checksum"):
        run_source_qualification(store_root=tmp_path, index=index)


def test_report_identity_matches_an_uninterrupted_run(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT", "ETHUSDT"])
    # Both roots pin their prospective holdout boundary at the same fixed first
    # authenticated instant; the resumed root then replays the boundary it pinned.
    clean = run_source_qualification(
        store_root=tmp_path / "clean", index=index, now=FIXED_QUALIFICATION_INSTANT
    )
    resumed_root = tmp_path / "resumed"
    first = run_source_qualification(
        store_root=resumed_root, index=index, now=FIXED_QUALIFICATION_INSTANT
    )
    second = run_source_qualification(store_root=resumed_root, index=index)
    assert second.resume["reused_samples"] > 0
    assert identity_bytes(first) == identity_bytes(second)
    # Execution-plane differences must not change the semantic identity of the result.
    assert identity_bytes(clean) == identity_bytes(second)


def test_sample_plan_is_persisted_before_download_and_prefers_smallest(tmp_path: Path) -> None:
    small = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h")],
        interval_map={"monthly/klines": ["1h"]},
        payload_by_stem={"1h": small},
        months=CONTIGUOUS_MONTHS,
    )
    prefix = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/"
    objs = list(index.objects[prefix])
    # Make the middle-regime bucket offer a large and a small candidate.
    big_key = f"{prefix}BTCUSDT-1h-2022-07.zip"
    index.objects[prefix] = [*objs, ListingObject(key=big_key, size=50_000_000)]
    index.bodies[vision_object_url(big_key)] = small
    index.bodies[vision_object_url(f"{big_key}.CHECKSUM")] = _checksum_text(
        small, big_key.rsplit("/", 1)[-1]
    )
    report = run_source_qualification(store_root=tmp_path, index=index)
    plan_path = Path(report.storage["sample_plan_path"])
    assert plan_path.is_file()
    plan = json.loads(plan_path.read_text())
    assert plan["budget_bytes"] == GATE1_NEW_DOWNLOAD_BUDGET_BYTES
    assert plan["max_object_bytes"] == GATE1_MAX_NEW_OBJECT_BYTES
    assert big_key not in {entry["key"] for entry in plan["entries"]}
    assert plan["new_download_bytes"] < 50_000_000


def test_oversized_object_emits_typed_sample_budget_block(tmp_path: Path) -> None:
    payload = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h"), ("daily/klines", "1h")],
        interval_map={"monthly/klines": ["1h"], "daily/klines": ["1h"]},
        payload_by_stem={"1h": payload},
        months=CONTIGUOUS_MONTHS,
    )
    for prefix, objects in list(index.objects.items()):
        for obj in objects:
            index.bodies[vision_object_url(obj.key)] = payload
            index.bodies[vision_object_url(f"{obj.key}.CHECKSUM")] = _checksum_text(
                payload, obj.key.rsplit("/", 1)[-1]
            )
        index.objects[prefix] = [
            ListingObject(key=obj.key, size=600_000_000) for obj in objects
        ]
    prefix = f"{vision_prefix('monthly', 'klines')}BTCUSDT/"

    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]

    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    trade = next(row for row in report.product_matrix if row.product == "binance_usdm_bar_1h")
    assert trade.sample_budget_blocked
    blocked = trade.sample_budget_blocked[0]
    assert blocked["kind"] == "sample_budget_exceeded"
    assert blocked["required_bytes"] == 600_000_000
    assert blocked["required_key"].startswith(prefix) or blocked["required_key"].startswith(
        f"{vision_prefix('daily', 'klines')}BTCUSDT/"
    )
    # The source is reachable and fully inventoried; only the sample budget is unmet.
    assert trade.authority != "inaccessible"
    assert trade.listed_object_count == 6
    assert "sample_budget_exceeded" in trade.reason
    assert report.sample_plan["blocked"]
    assert any(
        item["kind"] == "sample_budget_exceeded" for item in report.incidents
    )
    for objects in index.objects.values():
        for item in objects:
            assert vision_object_url(item.key) not in fetched


def test_sample_budget_does_not_cap_reported_source_size(tmp_path: Path) -> None:
    payload = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h")],
        interval_map={"monthly/klines": ["1h"]},
        payload_by_stem={"1h": payload},
    )
    prefix = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/"
    index.objects[prefix] = [
        ListingObject(key=f"{prefix}BTCUSDT-1h-{month}.zip", size=600_000_000)
        for month in ("2019-09", "2022-06", "2026-01")
    ]
    for obj in index.objects[prefix]:
        index.bodies[vision_object_url(obj.key)] = payload
    report = run_source_qualification(store_root=tmp_path, index=index)
    trade = next(row for row in report.product_matrix if row.product == "binance_usdm_bar_1h")
    # Full listed byte inventory is preserved, never truncated to the execution budget.
    assert trade.listed_bytes == 1_800_000_000
    assert report.storage["byte_count_exact"]["binance_usdm_bar_1h"] == 1_800_000_000


# --- review-68 surgical correction ---------------------------------------------------


class _InjectedAbort(RuntimeError):
    """A hard interruption that is not a qualification error."""


class _AlwaysFailingTransport:
    def __init__(self) -> None:
        self.calls = 0

    def stream_get(self, url: str, *, headers, timeout: TimeoutConfig) -> StreamResponse:
        self.calls += 1
        raise httpx.ConnectError("Connection reset by peer")


def _listing_store_with_two_prefixes(tmp_path: Path) -> tuple[ListingCheckpointStore, Path, dict]:
    cache = tmp_path / "list_cache"
    trades = vision_prefix("monthly", "trades")
    metrics = vision_prefix("daily", "metrics")
    pages = {
        (trades, None): _real_shaped_page(prefix=trades, prefixes=[f"{trades}BTCUSDT/"]),
        (metrics, None): _real_shaped_page(prefix=metrics, prefixes=[f"{metrics}ETHUSDT/"]),
    }
    path = tmp_path / "listing.json"
    store = ListingCheckpointStore.load(path, cache)
    index = TransportObjectIndex(
        _ScriptedTransport(pages),
        list_cache_dir=cache,
        checkpoint=store,
        retry=RetryRunner(sleeper=lambda _d: None, jitter=lambda d: d),
    )
    index.list_common_prefixes(trades)
    index.list_common_prefixes(metrics)
    return store, path, {"trades": trades, "metrics": metrics, "cache": cache, "pages": pages}


def test_cross_request_page_substitution_fails_closed(tmp_path: Path) -> None:
    store, path, ctx = _listing_store_with_two_prefixes(tmp_path)
    trades_key = listing_request_key(
        listing_request_identity(
            endpoint=VISION_S3_ENDPOINT,
            prefix=ctx["trades"],
            delimiter="/",
            continuation_token=None,
        )
    )
    metrics_key = listing_request_key(
        listing_request_identity(
            endpoint=VISION_S3_ENDPOINT,
            prefix=ctx["metrics"],
            delimiter="/",
            continuation_token=None,
        )
    )
    document = json.loads(path.read_text())
    metrics_entry = document["entries"][metrics_key]
    # Point the trades request at a different but internally valid retained page.
    document["entries"][trades_key]["response_sha256"] = metrics_entry["response_sha256"]
    document["entries"][trades_key]["content_path"] = metrics_entry["content_path"]
    path.write_text(json.dumps(document))

    reloaded = ListingCheckpointStore.load(path, ctx["cache"])
    index = TransportObjectIndex(
        _ScriptedTransport(ctx["pages"]),
        list_cache_dir=ctx["cache"],
        checkpoint=reloaded,
        retry=RetryRunner(sleeper=lambda _d: None, jitter=lambda d: d),
    )
    with pytest.raises(ResumeIntegrityError, match="does not echo the resumed request identity"):
        index.list_common_prefixes(ctx["trades"])


def test_listing_checkpoint_key_must_be_the_canonical_request_hash(tmp_path: Path) -> None:
    store, path, ctx = _listing_store_with_two_prefixes(tmp_path)
    document = json.loads(path.read_text())
    key = next(iter(document["entries"]))
    document["entries"]["not-the-canonical-hash"] = document["entries"].pop(key)
    path.write_text(json.dumps(document))
    with pytest.raises(ResumeIntegrityError, match="not the canonical hash"):
        ListingCheckpointStore.load(path, ctx["cache"])


def test_listing_checkpoint_content_path_must_be_cache_local(tmp_path: Path) -> None:
    store, path, ctx = _listing_store_with_two_prefixes(tmp_path)
    document = json.loads(path.read_text())
    key = next(iter(document["entries"]))
    document["entries"][key]["content_path"] = "/elsewhere/deadbeef"
    path.write_text(json.dumps(document))
    with pytest.raises(ResumeIntegrityError, match="cache-local content address"):
        ListingCheckpointStore.load(path, ctx["cache"])


def test_listing_checkpoint_pagination_metadata_must_match(tmp_path: Path) -> None:
    store, path, ctx = _listing_store_with_two_prefixes(tmp_path)
    document = json.loads(path.read_text())
    key = listing_request_key(
        listing_request_identity(
            endpoint=VISION_S3_ENDPOINT,
            prefix=ctx["trades"],
            delimiter="/",
            continuation_token=None,
        )
    )
    document["entries"][key]["next_continuation_token"] = "forged-token"
    path.write_text(json.dumps(document))
    reloaded = ListingCheckpointStore.load(path, ctx["cache"])
    index = TransportObjectIndex(
        _ScriptedTransport(ctx["pages"]),
        list_cache_dir=ctx["cache"],
        checkpoint=reloaded,
        retry=RetryRunner(sleeper=lambda _d: None, jitter=lambda d: d),
    )
    with pytest.raises(ResumeIntegrityError, match="pagination metadata"):
        index.list_common_prefixes(ctx["trades"])


@pytest.mark.parametrize(
    "body",
    [
        "{not json",
        json.dumps({"ticket": "CEX-002", "kind": "listing_checkpoint"}),
        json.dumps({"ticket": "OTHER", "kind": "listing_checkpoint", "version": 1}),
        json.dumps({"ticket": "CEX-002", "kind": "sample_checkpoint", "version": 1}),
        json.dumps({"ticket": "CEX-002", "kind": "listing_checkpoint", "version": 99}),
        json.dumps([1, 2, 3]),
    ],
)
def test_malformed_listing_checkpoint_document_fails_closed(tmp_path: Path, body: str) -> None:
    path = tmp_path / "listing.json"
    path.write_text(body)
    with pytest.raises(ResumeIntegrityError):
        ListingCheckpointStore.load(path, tmp_path / "cache")


@pytest.mark.parametrize(
    "body",
    [
        "{not json",
        json.dumps({"ticket": "CEX-002", "kind": "sample_checkpoint"}),
        json.dumps({"ticket": "CEX-002", "kind": "sample_checkpoint", "version": 1, "objects": []}),
    ],
)
def test_malformed_sample_checkpoint_document_fails_closed(tmp_path: Path, body: str) -> None:
    path = tmp_path / "progress.json"
    path.write_text(body)
    with pytest.raises(ResumeIntegrityError):
        SampleCheckpointStore.load(path)


def test_absent_checkpoint_documents_initialize_empty(tmp_path: Path) -> None:
    listing = ListingCheckpointStore.load(tmp_path / "missing.json", tmp_path / "cache")
    assert listing.entries == {}
    samples = SampleCheckpointStore.load(tmp_path / "missing-progress.json")
    assert samples.objects == {}
    journal = RetryJournal.load(tmp_path / "missing-journal.json")
    assert journal.incidents == []


def test_corrupt_sample_checkpoint_aborts_the_qualifier(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(store_root=tmp_path, index=index)
    progress = tmp_path / "cex002_qualification_progress.json"
    progress.write_text("{corrupted")
    with pytest.raises(ResumeIntegrityError):
        run_source_qualification(store_root=tmp_path, index=index)


def test_substituted_provider_checksum_in_checkpoint_fails_closed(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(store_root=tmp_path, index=index)
    progress = tmp_path / "cex002_qualification_progress.json"
    document = json.loads(progress.read_text())
    key = next(iter(document["objects"]))
    document["objects"][key]["provider_checksum"] = "b" * 64
    progress.write_text(json.dumps(document))
    with pytest.raises(ResumeIntegrityError, match="provider checksum disagrees"):
        run_source_qualification(store_root=tmp_path, index=index)


def test_sample_checkpoint_url_must_match_the_object_key(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(store_root=tmp_path, index=index)
    progress = tmp_path / "cex002_qualification_progress.json"
    document = json.loads(progress.read_text())
    key = next(iter(document["objects"]))
    document["objects"][key]["url"] = "https://data.binance.vision/data/other.zip"
    progress.write_text(json.dumps(document))
    with pytest.raises(ResumeIntegrityError, match="url does not match"):
        run_source_qualification(store_root=tmp_path, index=index)


def test_tampered_retained_sidecar_is_not_provider_authority(tmp_path: Path) -> None:
    cache = tmp_path / "list_cache"
    cache.mkdir(parents=True)
    digest = "c" * 64
    body = f"{digest}  BTCUSDT-trades-2020-01.zip\n".encode()
    blob = cache / hashlib.sha256(body).hexdigest()
    blob.write_bytes(body)
    checksums = RetainedChecksumIndex.from_cache(cache)
    key = "data/futures/um/monthly/trades/BTCUSDT/BTCUSDT-trades-2020-01.zip"
    assert checksums.lookup(key) is not None
    # Modify the sidecar after indexing: it no longer matches its content address.
    blob.write_bytes(f"{'d' * 64}  BTCUSDT-trades-2020-01.zip\n".encode())
    with pytest.raises(ResumeIntegrityError, match="no longer matches its content address"):
        checksums.lookup(key)


def test_sidecar_not_at_its_content_address_is_never_authority(tmp_path: Path) -> None:
    cache = tmp_path / "list_cache"
    cache.mkdir(parents=True)
    body = f"{'e' * 64}  BTCUSDT-trades-2020-01.zip\n".encode()
    (cache / ("f" * 64)).write_bytes(body)
    checksums = RetainedChecksumIndex.from_cache(cache)
    assert checksums.by_basename == {}


def test_unique_remote_object_is_charged_once(tmp_path: Path) -> None:
    payload = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h")],
        interval_map={"monthly/klines": ["1h"]},
        payload_by_stem={"1h": payload},
        months=("2020-01",),
    )
    prefix = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/"
    only_key = f"{prefix}BTCUSDT-1h-2020-01.zip"
    index.objects[prefix] = [ListingObject(key=only_key, size=10)]
    index.bodies[vision_object_url(only_key)] = payload
    index.bodies[vision_object_url(f"{only_key}.CHECKSUM")] = _checksum_text(
        payload, only_key.rsplit("/", 1)[-1]
    )
    report = run_source_qualification(store_root=tmp_path, index=index)
    plan = report.sample_plan
    # One physical object aliased to three regimes is charged and fetched exactly once.
    assert plan["new_download_bytes"] == 10
    assert plan["unique_new_objects"] == 1
    actions = [entry["action"] for entry in plan["entries"] if entry["key"] == only_key]
    assert sorted(actions) == ["alias", "alias", "download"]
    assert len({item.key for item in report.samples}) == 1
    assert {item.regime for item in report.samples} == {"early", "middle", "recent"}


def test_retained_object_is_reported_once(tmp_path: Path) -> None:
    payload = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h")],
        interval_map={"monthly/klines": ["1h"]},
        payload_by_stem={"1h": payload},
        months=("2020-01",),
    )
    prefix = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/"
    only = index.objects[prefix][0]
    index.objects[prefix] = [only]
    first = run_source_qualification(store_root=tmp_path, index=index)
    first_plan = first.sample_plan
    first_ledger = json.loads((tmp_path / BUDGET_LEDGER_FILENAME).read_text())
    first_disposition = first_ledger["charges"][only.key]["disposition"]

    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    second = run_source_qualification(store_root=tmp_path, index=index)
    assert second.plan_lock["plan_version"] == first.plan_lock["plan_version"]
    assert second.plan_lock["plan_digest"] == first.plan_lock["plan_digest"]
    assert second.sample_plan["entries"] == first.sample_plan["entries"]
    for field in (
        "new_download_bytes",
        "unique_new_objects",
        "unique_retained_objects",
        "retained_bytes",
    ):
        assert second.sample_plan[field] == first_plan[field]
    assert first_plan["new_download_bytes"] > 0
    assert first_plan["unique_new_objects"] == 1
    assert first_plan["unique_retained_objects"] == 0
    assert first_plan["retained_bytes"] == 0
    second_ledger = json.loads((tmp_path / BUDGET_LEDGER_FILENAME).read_text())
    assert second_ledger["charges"] == first_ledger["charges"]
    assert second_ledger["charges"][only.key]["disposition"] == first_disposition
    assert second.resume["reused_samples"] > 0
    assert vision_object_url(only.key) not in fetched
    assert vision_object_url(f"{only.key}.CHECKSUM") not in fetched
    assert second.budget["no_transfer_object_count"] == 0
    assert second.budget["settled_bytes"] == first.budget["settled_bytes"]


def test_retry_attempt_bound_is_not_multiplied_per_request(tmp_path: Path) -> None:
    transport = _AlwaysFailingTransport()
    retry = RetryRunner(
        policy=RetryPolicy(max_attempts=3), sleeper=lambda _d: None, jitter=lambda d: d
    )
    index = TransportObjectIndex(transport, list_cache_dir=tmp_path, retry=retry)
    with pytest.raises(SourceQualificationError, match="bounded attempt limit"):
        index.fetch_bytes(vision_object_url("data/futures/um/monthly/trades/x.zip"))
    # Exactly one bounded policy owns the request: three attempts, not three squared.
    assert transport.calls == 3
    assert retry.retries == 2


def test_retry_incidents_survive_an_aborted_run(tmp_path: Path) -> None:
    journal_path = tmp_path / "journal.json"
    retry = RetryRunner(
        policy=RetryPolicy(max_attempts=2),
        sleeper=lambda _d: None,
        jitter=lambda d: d,
        journal=RetryJournal.load(journal_path),
    )
    index = TransportObjectIndex(
        _AlwaysFailingTransport(), list_cache_dir=tmp_path, retry=retry
    )
    with pytest.raises(SourceQualificationError):
        index.fetch_bytes(vision_object_url("data/futures/um/monthly/trades/x.zip"))
    # The journal is durable on disk even though no report was ever returned.
    reloaded = RetryJournal.load(journal_path)
    assert len(reloaded.incidents) == 2
    assert all("?" not in item["label"] for item in reloaded.incidents)


def _distinct_bytes_index() -> MemoryObjectIndex:
    """Two symbols whose every remote object carries its own bytes and sidecar."""
    return _index_with_family(
        symbols=["BTCUSDT", "ETHUSDT"],
        families=[("monthly/trades", "trades"), ("monthly/klines", "1h")],
        interval_map={"monthly/klines": ["1h"]},
        payload_for_key=_distinct_object_payload,
    )


def test_abort_after_completed_sample_resumes_missing_objects_only(tmp_path: Path) -> None:
    clean_index = _distinct_bytes_index()
    # Both roots pin their prospective holdout boundary at the same fixed first
    # authenticated instant, so the comparison is over semantics rather than two
    # independently pinned boundaries.
    clean = run_source_qualification(
        store_root=tmp_path / "clean", index=clean_index, now=FIXED_QUALIFICATION_INSTANT
    )

    store_root = tmp_path / "resumed"
    aborting = _distinct_bytes_index()
    real_fetch = aborting.fetch_bytes
    completed = {"n": 0}

    def _abort_after_two(url: str) -> bytes:
        if not url.endswith(".CHECKSUM"):
            if completed["n"] >= 2:
                raise _InjectedAbort(url)
            completed["n"] += 1
        return real_fetch(url)

    aborting.fetch_bytes = _abort_after_two  # type: ignore[method-assign]
    with pytest.raises(_InjectedAbort):
        run_source_qualification(
            store_root=store_root, index=aborting, now=FIXED_QUALIFICATION_INSTANT
        )

    progress = json.loads((store_root / "cex002_qualification_progress.json").read_text())
    done_keys = set(progress["objects"])
    assert len(done_keys) == 2

    resumed_index = _distinct_bytes_index()
    # Every object outside the pre-abort checkpoint is genuinely absent from the
    # content-addressed store, including the one whose provider sidecar was already
    # retained when the abort fired. Nothing else can stand in for its bytes.
    sample_store = store_root / "raw" / "sha256"
    assert {path.name for path in sample_store.iterdir() if len(path.name) == 64} == {
        hashlib.sha256(resumed_index.bodies[vision_object_url(key)]).hexdigest()
        for key in done_keys
    }

    fetched: list[str] = []
    resume_fetch = resumed_index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return resume_fetch(url)

    resumed_index.fetch_bytes = _tracking  # type: ignore[method-assign]
    resumed = run_source_qualification(store_root=store_root, index=resumed_index)

    # Objects proven before the abort are never fetched again.
    for key in done_keys:
        assert vision_object_url(key) not in fetched
    remaining = {item.key for item in resumed.samples} - done_keys
    assert remaining
    for key in remaining:
        assert vision_object_url(key) in fetched
    # The interrupted-then-resumed result is semantically identical to a clean run.
    assert identity_bytes(resumed) == identity_bytes(clean)


def _aborted_same_digest_state(store_root: Path) -> tuple[MemoryObjectIndex, str, str]:
    """Interrupt after one object when remaining keys share that object's digest.

    The in-memory acquire path reuses a valid content-addressed destination without a
    second raw fetch, so the interrupt is injected after the pending key's provider
    sidecar is retained and before that key is checkpointed. Returns the index, the
    proven key, and the key whose sidecar exists while its raw URL was never fetched.
    """
    from cryptofactors.acquisition import binance_usdm_harmonic_qualification as module

    index = _trades_index(["BTCUSDT"])
    real_persist = module.persist_provider_sidecar
    persisted = {"n": 0}

    def _persist_then_abort(body: bytes, *, sidecar_dir: Path) -> tuple[Path, str]:
        dest, digest = real_persist(body, sidecar_dir=sidecar_dir)
        persisted["n"] += 1
        if persisted["n"] >= 2:
            raise _InjectedAbort(digest)
        return dest, digest

    module.persist_provider_sidecar = _persist_then_abort  # type: ignore[method-assign]
    try:
        with pytest.raises(_InjectedAbort):
            run_source_qualification(store_root=store_root, index=index)
    finally:
        module.persist_provider_sidecar = real_persist  # type: ignore[method-assign]

    document = json.loads((store_root / "cex002_qualification_progress.json").read_text())
    proven_key = next(iter(document["objects"]))
    prefix = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/"
    checksums = RetainedChecksumIndex.from_cache(store_root / "list_cache")
    pending_key = next(
        obj.key
        for obj in index.objects[prefix]
        if obj.key not in document["objects"] and checksums.lookup(obj.key) is not None
    )
    assert proven_key != pending_key
    return index, proven_key, pending_key


def test_same_digest_cross_key_recovery_skips_the_redundant_raw_fetch(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    index, proven_key, pending_key = _aborted_same_digest_state(store_root)
    evidence = RetainedChecksumIndex.from_cache(store_root / "list_cache").lookup(pending_key)
    assert evidence is not None
    digest = str(evidence["provider_checksum"])
    # These synthetic objects legitimately share bytes, so the blob retained under the
    # proven key already sits at the pending object's content address.
    assert (store_root / "raw" / "sha256" / digest).is_file()

    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    resumed = run_source_qualification(store_root=store_root, index=index)

    # Exact sidecar filename, sidecar content address, provider checksum and rehashed raw
    # bytes all agree, so the pending object is adopted with no redundant raw retrieval.
    assert resumed.resume["recovered_samples"] == 1
    assert vision_object_url(pending_key) not in fetched
    assert vision_object_url(proven_key) not in fetched
    recovered = next(item for item in resumed.samples if item.key == pending_key)
    assert recovered.sha256 == digest
    assert recovered.reused_existing is True


@pytest.mark.parametrize(
    "broken_leg", ["sidecar_filename", "sidecar_content_address", "provider_checksum"]
)
def test_same_digest_cross_key_recovery_requires_every_leg(
    tmp_path: Path, broken_leg: str
) -> None:
    store_root = tmp_path / "store"
    index, _proven_key, pending_key = _aborted_same_digest_state(store_root)
    cache = store_root / "list_cache"
    evidence = RetainedChecksumIndex.from_cache(cache).lookup(pending_key)
    assert evidence is not None
    digest = str(evidence["provider_checksum"])
    basename = pending_key.rsplit("/", 1)[-1]
    Path(str(evidence["content_path"])).unlink()

    if broken_leg == "sidecar_filename":
        # Retained digest and content address are intact, but it names another object.
        body = f"{digest}  BTCUSDT-trades-1999-01.zip\n".encode()
        (cache / hashlib.sha256(body).hexdigest()).write_bytes(body)
    elif broken_leg == "sidecar_content_address":
        # Correct digest and filename, but not stored at its own content address.
        body = f"{digest}  {basename}\n".encode()
        (cache / ("a" * 64)).write_bytes(body)
    else:
        # Correctly addressed and named, but it claims a digest that is not retained.
        body = f"{'b' * 64}  {basename}\n".encode()
        (cache / hashlib.sha256(body).hexdigest()).write_bytes(body)

    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    resumed = run_source_qualification(store_root=store_root, index=index)

    # One broken leg withdraws recovery: the pending key is not adopted from the
    # interrupted checkpoint path. Acquire then either re-proves the sidecar and
    # reuses a valid destination, or fetches the raw object when dest is not valid.
    pending_raw = vision_object_url(pending_key)
    pending_checksum = vision_object_url(f"{pending_key}.CHECKSUM")
    assert resumed.resume["recovered_samples"] == 0
    if broken_leg == "provider_checksum":
        assert pending_raw in fetched
    else:
        assert pending_checksum in fetched
        assert pending_raw not in fetched


def test_same_digest_cross_key_recovery_fails_closed_on_tampered_bytes(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    index, _proven_key, pending_key = _aborted_same_digest_state(store_root)
    evidence = RetainedChecksumIndex.from_cache(store_root / "list_cache").lookup(pending_key)
    assert evidence is not None
    (store_root / "raw" / "sha256" / str(evidence["provider_checksum"])).write_bytes(b"tampered")
    with pytest.raises(ResumeIntegrityError, match="do not match the retained provider checksum"):
        run_source_qualification(store_root=store_root, index=index)


# --- review-69 retained-sidecar authority --------------------------------------------


def _first_sample_run(tmp_path: Path) -> tuple[MemoryObjectIndex, object, Path]:
    index = _trades_index(["BTCUSDT"])
    report = run_source_qualification(store_root=tmp_path, index=index)
    return index, report, tmp_path / "cex002_qualification_progress.json"


def test_every_sample_checkpoint_records_a_retained_sidecar(tmp_path: Path) -> None:
    index, report, progress = _first_sample_run(tmp_path)
    document = json.loads(progress.read_text())
    assert document["objects"]
    for key, entry in document["objects"].items():
        sidecar = Path(entry["provider_checksum_path"])
        # Even an in-memory index must leave the sidecar retained content-addressably.
        assert sidecar.is_file()
        assert sidecar.parent == tmp_path / "list_cache"
        assert sidecar.name == entry["provider_checksum_sha256"]
        assert hashlib.sha256(sidecar.read_bytes()).hexdigest() == sidecar.name
        tokens = sidecar.read_text().strip().split()
        assert tokens[0] == entry["provider_checksum"] == entry["sha256"]
        assert tokens[1] == key.rsplit("/", 1)[-1]


def test_intact_sidecar_resumes_without_any_network_fetch(tmp_path: Path) -> None:
    index, first, _progress = _first_sample_run(tmp_path)
    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    second = run_source_qualification(store_root=tmp_path, index=index)
    assert second.resume["reused_samples"] > 0
    # Neither the sample nor its sidecar is refetched on a proven resume.
    for sample in second.samples:
        assert sample.url not in fetched
        assert f"{sample.url}.CHECKSUM" not in fetched
    assert identity_bytes(first) == identity_bytes(second)


def test_resume_fails_closed_when_the_sidecar_is_deleted(tmp_path: Path) -> None:
    index, _first, progress = _first_sample_run(tmp_path)
    document = json.loads(progress.read_text())
    entry = next(iter(document["objects"].values()))
    Path(entry["provider_checksum_path"]).unlink()
    with pytest.raises(ResumeIntegrityError, match="sidecar is missing from the retained store"):
        run_source_qualification(store_root=tmp_path, index=index)


def test_resume_fails_closed_when_the_sidecar_bytes_are_tampered(tmp_path: Path) -> None:
    index, _first, progress = _first_sample_run(tmp_path)
    document = json.loads(progress.read_text())
    entry = next(iter(document["objects"].values()))
    Path(entry["provider_checksum_path"]).write_bytes(b"tampered sidecar\n")
    with pytest.raises(ResumeIntegrityError, match="do not match the recorded blob digest"):
        run_source_qualification(store_root=tmp_path, index=index)


def test_resume_fails_closed_when_the_sidecar_is_relocated(tmp_path: Path) -> None:
    index, _first, progress = _first_sample_run(tmp_path)
    document = json.loads(progress.read_text())
    key = next(iter(document["objects"]))
    entry = document["objects"][key]
    moved = tmp_path / "elsewhere" / entry["provider_checksum_sha256"]
    moved.parent.mkdir(parents=True, exist_ok=True)
    moved.write_bytes(Path(entry["provider_checksum_path"]).read_bytes())
    entry["provider_checksum_path"] = str(moved)
    progress.write_text(json.dumps(document))
    with pytest.raises(ResumeIntegrityError, match="not its cache-local content address"):
        run_source_qualification(store_root=tmp_path, index=index)


def test_resume_fails_closed_on_a_substituted_sidecar_digest(tmp_path: Path) -> None:
    index, _first, progress = _first_sample_run(tmp_path)
    document = json.loads(progress.read_text())
    entries = list(document["objects"].values())
    assert len(entries) >= 2
    # Point one object's checkpoint at another object's genuine, intact sidecar.
    entries[0]["provider_checksum_path"] = entries[1]["provider_checksum_path"]
    entries[0]["provider_checksum_sha256"] = entries[1]["provider_checksum_sha256"]
    progress.write_text(json.dumps(document))
    with pytest.raises(ResumeIntegrityError, match="names a different object"):
        run_source_qualification(store_root=tmp_path, index=index)


def test_sample_checkpoint_without_sidecar_identity_fails_closed(tmp_path: Path) -> None:
    index, _first, progress = _first_sample_run(tmp_path)
    document = json.loads(progress.read_text())
    for entry in document["objects"].values():
        entry.pop("provider_checksum_path", None)
        entry.pop("provider_checksum_sha256", None)
    progress.write_text(json.dumps(document))
    with pytest.raises(ResumeIntegrityError, match="sidecar digest is not a 64-character"):
        run_source_qualification(store_root=tmp_path, index=index)


KEY_UNDER_TEST = "data/futures/um/monthly/trades/BTCUSDT/BTCUSDT-trades-2020-01.zip"


def _write_sidecar(cache: Path, body: bytes) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    blob = cache / hashlib.sha256(body).hexdigest()
    blob.write_bytes(body)
    return blob


def test_verify_provider_sidecar_rejects_a_foreign_filename(tmp_path: Path) -> None:
    cache = tmp_path / "list_cache"
    digest = "a" * 64
    blob = _write_sidecar(cache, f"{digest}  SOME-OTHER-OBJECT.zip\n".encode())
    with pytest.raises(ResumeIntegrityError, match="names a different object"):
        verify_provider_sidecar(
            key=KEY_UNDER_TEST,
            object_sha256=digest,
            sidecar_path=blob,
            sidecar_sha256=blob.name,
            sidecar_dir=cache,
        )


def test_verify_provider_sidecar_rejects_a_disagreeing_checksum(tmp_path: Path) -> None:
    cache = tmp_path / "list_cache"
    blob = _write_sidecar(
        cache, f"{'a' * 64}  BTCUSDT-trades-2020-01.zip\n".encode()
    )
    with pytest.raises(ResumeIntegrityError, match="disagrees with the retained object digest"):
        verify_provider_sidecar(
            key=KEY_UNDER_TEST,
            object_sha256="b" * 64,
            sidecar_path=blob,
            sidecar_sha256=blob.name,
            sidecar_dir=cache,
        )


def test_verify_provider_sidecar_rejects_more_than_one_record(tmp_path: Path) -> None:
    cache = tmp_path / "list_cache"
    digest = "a" * 64
    body = (
        f"{digest}  BTCUSDT-trades-2020-01.zip\n"
        f"{digest}  BTCUSDT-trades-2020-02.zip\n"
    ).encode()
    blob = _write_sidecar(cache, body)
    with pytest.raises(ResumeIntegrityError, match="exactly one checksum and filename"):
        verify_provider_sidecar(
            key=KEY_UNDER_TEST,
            object_sha256=digest,
            sidecar_path=blob,
            sidecar_sha256=blob.name,
            sidecar_dir=cache,
        )


def test_verify_provider_sidecar_accepts_intact_evidence(tmp_path: Path) -> None:
    cache = tmp_path / "list_cache"
    digest = "a" * 64
    blob = _write_sidecar(cache, f"{digest}  BTCUSDT-trades-2020-01.zip\n".encode())
    assert (
        verify_provider_sidecar(
            key=KEY_UNDER_TEST,
            object_sha256=digest,
            sidecar_path=blob,
            sidecar_sha256=blob.name,
            sidecar_dir=cache,
        )
        == digest
    )


# --- review-75 membership authority ---------------------------------------------------


def _trades_index(symbols: list[str], **kwargs: Any) -> MemoryObjectIndex:
    payloads = dict(kwargs.pop("payload_by_stem", None) or {})
    payloads.setdefault(
        "1h", _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    )
    intervals = dict(kwargs.pop("interval_map", None) or {})
    intervals.setdefault("monthly/klines", ["1h"])
    return _index_with_family(
        symbols=symbols,
        families=[("monthly/trades", "trades"), ("monthly/klines", "1h")],
        interval_map=intervals,
        payload_by_stem=payloads,
        months=CONTIGUOUS_MONTHS,
        **kwargs,
    )


def test_exchange_rows_retain_contract_identity_fields() -> None:
    rows = parse_exchange_info_rows(_load_json("exchange_info.json"))
    assert rows["BTCUSDT"]["contract_type"] == "PERPETUAL"
    assert rows["BTCUSDT"]["status"] == "TRADING"
    assert rows["BTCUSDT"]["underlying_type"] == "COIN"
    assert rows["BTCUSDT_240329"]["contract_type"] == "CURRENT_QUARTER"
    # A TradFi continuous contract is retained in full so it can be excluded on evidence.
    assert rows["AAPLUSDT"]["underlying_type"] == "TRADIFI"
    assert "AAPLUSDT" not in parse_current_perpetuals(_load_json("exchange_info.json"))


def test_archive_name_alone_never_confirms_membership(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    report = run_source_qualification(store_root=tmp_path, index=index)
    # The name is inventoried, but nothing official proves it is a perpetual.
    assert report.discovered_symbols == ("BTCUSDT",)
    assert report.accepted_universe == ()
    assert report.membership["resolved"] is False
    assert report.membership["universe_basis"] == "unresolved_archive_union"
    assert report.membership["classes"][MEMBERSHIP_UNRESOLVED] == ["BTCUSDT"]
    membership = _row("binance_usdm_perpetual_membership", report)
    assert membership.source_qualification_state == SOURCE_STATE_MEMBERSHIP
    assert membership.authority == "membership_unresolved"
    assert membership.coverage_state == COVERAGE_UNRESOLVED_MEMBERSHIP
    assert "binance_usdm_perpetual_membership" in report.blocked_products


def test_delivery_settlement_and_dated_names_are_classified_separately(tmp_path: Path) -> None:
    index = _trades_index(
        ["AERGOUSDTSETTLEDSETTLED", "BTCUSDT", "BTCUSDT_210326", "ETHUSDT_240927", "ZZZUSDT"]
    )
    delivery_row = {
        "symbol": "BTCUSDT_210326",
        "pair": "BTCUSDT",
        "contractType": "CURRENT_QUARTER",
        "status": "TRADING",
        "underlyingType": "COIN",
        "baseAsset": "BTC",
        "quoteAsset": "USDT",
        "marginAsset": "USDT",
        "onboardDate": DEFAULT_ONBOARD_MS,
        "deliveryDate": 1_616_716_800_000,
    }
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT", extra=[delivery_row]),
    )
    classes = report.membership["classes"]
    # Official evidence resolves the delivery contract; spelling resolves nothing.
    assert classes[MEMBERSHIP_CONFIRMED] == ["BTCUSDT"]
    assert classes[MEMBERSHIP_DELIVERY] == ["BTCUSDT_210326"]
    assert classes[MEMBERSHIP_SETTLEMENT_ARTIFACT] == ["AERGOUSDTSETTLEDSETTLED"]
    assert classes[MEMBERSHIP_DATED_DELIVERY] == ["ETHUSDT_240927"]
    assert classes[MEMBERSHIP_UNRESOLVED] == ["ZZZUSDT"]
    assert report.accepted_universe == ("BTCUSDT",)
    assert report.membership["resolved"] is False
    assert set(report.membership["unresolved_symbols"]) == {
        "AERGOUSDTSETTLEDSETTLED",
        "ETHUSDT_240927",
        "ZZZUSDT",
    }
    # Every observed name is still reported; none is silently dropped.
    assert {item["symbol"] for item in report.membership["classifications"]} == set(
        report.discovered_symbols
    )


def test_realized_funding_archive_confirms_perpetual_membership(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/trades", "trades"), ("monthly/fundingRate", "fundingRate")],
        payload_by_stem={
            "fundingRate": _zip_bytes("f.csv", (FIXTURES / "headed_funding.csv").read_bytes())
        },
        months=CONTIGUOUS_MONTHS,
    )
    report = run_source_qualification(store_root=tmp_path, index=index)
    # No exchangeInfo at all: only a perpetual realizes funding, so the archive proves it.
    assert report.accepted_universe == ("BTCUSDT",)
    assert report.membership["resolved"] is True
    evidence = report.membership["classifications"][0]["evidence"]
    assert [item["kind"] for item in evidence] == ["official_realized_funding_observation"]


def test_retained_contract_metadata_confirms_a_later_delisted_perpetual(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT", "OLDUSDT"])
    first = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT", "OLDUSDT")
    )
    assert set(first.accepted_universe) == {"BTCUSDT", "OLDUSDT"}

    # OLDUSDT is delisted. Its membership is still proved, but only by reparsing the
    # retained response bytes rather than by trusting a copied field.
    store = OfficialContractMetadataStore.load(
        tmp_path / CONTRACT_METADATA_FILENAME,
        snapshot_dir=tmp_path / CONTRACT_SNAPSHOT_DIRNAME,
    )
    historical = store.historical_rows()
    assert historical["OLDUSDT"]["contract_type"] == "PERPETUAL"
    classifications = classify_membership(
        discovered=["BTCUSDT", "OLDUSDT"],
        current_rows=parse_exchange_info_rows(_exchange_info("BTCUSDT")),
        historical_rows=historical,
        funding_evidence={},
    )
    old = next(item for item in classifications if item.symbol == "OLDUSDT")
    assert old.membership_class == MEMBERSHIP_CONFIRMED
    assert [item["kind"] for item in old.evidence] == ["retained_official_contract_metadata"]

    # A delisting is a genuine membership-authority change, so the locked plan refuses to
    # continue until a new plan version is authorized.
    with pytest.raises(ResumeIntegrityError, match="locked Gate 1 plan inputs changed") as err:
        run_source_qualification(
            store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
        )
    assert "membership_digest" in err.value.context["changed"]


# --- review-75 immutable plan and cumulative budget -----------------------------------


def _append_object(index: MemoryObjectIndex, key: str, payload: bytes) -> None:
    prefix = key.rsplit("/", 1)[0] + "/"
    index.objects[prefix] = [*index.objects[prefix], ListingObject(key=key, size=len(payload))]
    index.bodies[vision_object_url(key)] = payload
    index.bodies[vision_object_url(f"{key}.CHECKSUM")] = _checksum_text(
        payload, key.rsplit("/", 1)[-1]
    )


def test_locked_plan_is_replayed_on_a_normal_resume(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    first = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    planned = [entry["key"] for entry in first.sample_plan["entries"]]
    assert first.plan_lock["plan_version"] == 1
    assert first.plan_lock["state"] == "locked"

    second = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    # Execution progress against the same plan is not an input change.
    assert [entry["key"] for entry in second.sample_plan["entries"]] == planned
    assert second.plan_lock["plan_version"] == 1
    assert second.plan_lock["plan_digest"] == first.plan_lock["plan_digest"]
    lock = SamplePlanLock.load(tmp_path / SAMPLE_PLAN_LOCK_FILENAME)
    assert lock is not None
    assert [entry["key"] for entry in lock.plan["entries"]] == planned


def test_changed_inventory_blocks_the_locked_plan_before_download(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"
    extra = f"{prefix}BTCUSDT-trades-2020-04.zip"
    _append_object(
        index, extra, _zip_bytes("t.csv", (FIXTURES / "headerless_trades.csv").read_bytes())
    )
    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    with pytest.raises(ResumeIntegrityError, match="locked Gate 1 plan inputs changed") as err:
        run_source_qualification(
            store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
        )
    # A genuine input change fails closed, and nothing is downloaded first.
    assert err.value.context["kind"] == PLAN_INPUTS_CHANGED
    assert "inventory_digest" in err.value.context["changed"]
    assert fetched == []


def test_valid_json_plan_tamper_fails_closed(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    lock_path = tmp_path / SAMPLE_PLAN_LOCK_FILENAME
    document = json.loads(lock_path.read_text())
    for entry in document["plan"]["entries"]:
        if entry["action"] == "download":
            # Relabelling a download would slip the object past the pre-download budget
            # guard while still allowing acquisition.
            entry["action"] = "reuse_retained"
            break
    lock_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ResumeIntegrityError, match="does not match its recorded digest"):
        run_source_qualification(
            store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
        )


def test_digest_consistent_plan_tamper_still_fails_validation(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    lock_path = tmp_path / SAMPLE_PLAN_LOCK_FILENAME
    document = json.loads(lock_path.read_text())
    for entry in document["plan"]["entries"]:
        if entry["action"] == "download":
            entry["action"] = "reuse_retained"
            break
    document["plan_digest"] = plan_content_digest(SamplePlan.from_dict(document["plan"]))
    lock_path.write_text(json.dumps(document), encoding="utf-8")
    # Recomputing the digest does not make the plan internally consistent.
    with pytest.raises(ResumeIntegrityError, match="download bytes disagree"):
        run_source_qualification(
            store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
        )


def test_plan_validation_refuses_unknown_actions_and_foreign_urls() -> None:
    key = f"{vision_prefix('monthly', 'trades')}BTCUSDT/BTCUSDT-trades-2020-01.zip"
    good = SamplePlanEntry(
        family="monthly/trades",
        symbol="BTCUSDT",
        regime="early",
        products=("binance_usdm_bar_1h",),
        key=key,
        url=vision_object_url(key),
        byte_size=10,
        action="download",
    )
    validate_sample_plan(
        SamplePlan(
            entries=(good,),
            blocked=(),
            new_download_bytes=10,
            retained_bytes=0,
            budget_bytes=100,
            max_object_bytes=100,
            unique_new_objects=1,
            allowance_bytes=100,
        )
    )
    with pytest.raises(ResumeIntegrityError, match="unknown action"):
        validate_sample_plan(
            SamplePlan(
                entries=(replace(good, action="fetch"),),
                blocked=(),
                new_download_bytes=10,
                retained_bytes=0,
                budget_bytes=100,
                max_object_bytes=100,
                unique_new_objects=1,
                allowance_bytes=100,
            )
        )
    with pytest.raises(ResumeIntegrityError, match="URL does not address its key"):
        validate_sample_plan(
            SamplePlan(
                entries=(replace(good, url="https://example.invalid/x.zip"),),
                blocked=(),
                new_download_bytes=10,
                retained_bytes=0,
                budget_bytes=100,
                max_object_bytes=100,
                unique_new_objects=1,
                allowance_bytes=100,
            )
        )


def test_sample_plan_to_dict_is_json_native_and_round_trippable() -> None:
    download_key = f"{vision_prefix('monthly', 'trades')}BTCUSDT/BTCUSDT-trades-2020-01.zip"
    blocked_key = f"{vision_prefix('monthly', 'trades')}ETHUSDT/ETHUSDT-trades-2020-01.zip"
    products = ("binance_usdm_perpetual_membership", "binance_usdm_bar_1h")
    plan = SamplePlan(
        entries=(
            SamplePlanEntry(
                family="monthly/trades",
                symbol="BTCUSDT",
                regime="early",
                products=products,
                key=download_key,
                url=vision_object_url(download_key),
                byte_size=10,
                action="download",
            ),
            SamplePlanEntry(
                family="monthly/trades",
                symbol="ETHUSDT",
                regime="early",
                products=products,
                key=blocked_key,
                url=vision_object_url(blocked_key),
                byte_size=600_000_000,
                action="blocked",
                block_reason="sample_budget_exceeded",
            ),
        ),
        blocked=(
            {
                "kind": "sample_budget_exceeded",
                "family": "monthly/trades",
                "symbol": "ETHUSDT",
                "regime": "early",
                "products": list(products),
                "required_key": blocked_key,
                "required_bytes": 600_000_000,
            },
        ),
        new_download_bytes=10,
        retained_bytes=0,
        budget_bytes=100,
        max_object_bytes=100,
        unique_new_objects=1,
        allowance_bytes=100,
    )
    serialized = plan.to_dict()
    assert all(isinstance(entry["products"], list) for entry in serialized["entries"])
    assert serialized["entries"][0]["products"] == list(products)
    assert serialized["blocked"]
    persisted = json.loads(json.dumps(serialized))
    assert persisted == serialized
    rebuilt = SamplePlan.from_dict(persisted)
    assert isinstance(rebuilt.entries[0].products, tuple)
    assert rebuilt.to_dict() == persisted
    assert plan_content_digest(rebuilt) == plan_content_digest(plan)
    validate_sample_plan(rebuilt)


def test_no_public_switch_can_reselect_the_locked_plan() -> None:
    assert "relock_sample_plan" not in inspect.signature(run_source_qualification).parameters
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "research"
        / "qualify_binance_usdm_harmonic_sources.py"
    )
    source = script.read_text(encoding="utf-8")
    # A new plan version requires a fresh reviewer authorization, not a CLI flag. The
    # exact parameter and flag are the boundary; explanatory prose is not.
    assert "--relock-sample-plan" not in source
    flags: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != "add_argument":
                continue
            flags.extend(
                arg.value
                for arg in node.args
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
            )
    assert flags
    assert not any("relock" in flag for flag in flags)


def test_new_download_budget_is_cumulative_across_invocations(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    prefix = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/"
    one_object = int(index.objects[prefix][0].size or 0)
    assert one_object > 0
    first = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT"),
        sample_budget_bytes=one_object,
    )
    assert first.sample_plan["new_download_bytes"] == one_object
    assert first.budget["charged_bytes"] == one_object
    assert first.budget["settled_object_count"] == 1
    assert first.budget["exhausted"] is True

    second = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT"),
        sample_budget_bytes=one_object,
    )
    # A new invocation replays the locked plan and does not restore the allowance.
    assert second.budget["charged_bytes"] == one_object
    assert second.budget["cumulative_remaining_bytes"] == 0
    assert second.budget["exhausted"] is True
    # With the allowance already spent, no new byte can be planned at all.
    exhausted_plan = build_sample_plan(
        inventory=build_family_inventory(index),
        family_products=family_product_map(),
        sample_symbols=["BTCUSDT"],
        delisted=[],
        retained_keys={},
        budget_bytes=one_object,
        max_object_bytes=GATE1_MAX_NEW_OBJECT_BYTES,
        cumulative_spent_bytes=one_object,
    )
    assert exhausted_plan.allowance_bytes == 0
    assert exhausted_plan.new_download_bytes == 0
    assert exhausted_plan.blocked


def test_pre_ledger_retained_bytes_are_an_explicit_unresolved_lower_bound(
    tmp_path: Path,
) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    (tmp_path / BUDGET_LEDGER_FILENAME).unlink()
    resumed = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    progress = json.loads((tmp_path / "cex002_qualification_progress.json").read_text())
    unique = {
        str(entry["sha256"]): int(entry["byte_size"]) for entry in progress["objects"].values()
    }
    # Pre-ledger spend cannot be attributed per invocation, so it is bounded, not assumed.
    # Pre-ledger spend cannot be attributed per invocation and includes review-67
    # budget-free samples, so it is an honest range, never a lower bound.
    assert resumed.budget["legacy_state"] == LEGACY_BUDGET_UNRESOLVED
    assert resumed.budget["legacy_chargeable_min_bytes"] == 0
    assert resumed.budget["legacy_chargeable_max_bytes"] == sum(unique.values())
    assert resumed.budget["cumulative_spent_min_bytes"] == 0
    assert resumed.budget["cumulative_spent_max_bytes"] == sum(unique.values())
    assert resumed.budget["breach_state"] == "none"
    assert resumed.budget["external_breach_record"].endswith(
        "74_CEX002_GATE1_RESUMABLE_EXECUTION.md"
    )

    # Against a smaller allowance the same retained evidence cannot prove the contract was
    # met: the breach is unresolved and the remaining allowance stays at zero.
    (tmp_path / BUDGET_LEDGER_FILENAME).unlink()
    ledger = BudgetLedger.bootstrap(
        tmp_path / BUDGET_LEDGER_FILENAME,
        budget_bytes=1,
        retained_objects=json.loads(
            (tmp_path / "cex002_qualification_progress.json").read_text()
        )["objects"],
        sample_dir=tmp_path / "raw" / "sha256",
        sidecar_dir=tmp_path / "list_cache",
    )
    assert ledger.breach_state == "unresolved"
    assert ledger.remaining_bytes == 0
    assert ledger.spent_min_bytes == 0


# --- review-75 physical storage feasibility -------------------------------------------


def test_physical_storage_requirement_is_deduplicated_and_reports_shortfall(
    tmp_path: Path,
) -> None:
    kline_zip = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h"), ("daily/klines", "1h")],
        interval_map={"monthly/klines": ["1h"], "daily/klines": ["1h"]},
        payload_by_stem={"1h": kline_zip},
        months=CONTIGUOUS_MONTHS,
    )
    for prefix in list(index.objects):
        index.objects[prefix] = [
            ListingObject(key=obj.key, size=100_000_000_000_000)
            for obj in index.objects[prefix]
        ]
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    requirement = report.storage["physical_source_requirement"]
    # Daily copies of a completed month are not dual-counted once monthly objects exist.
    assert requirement["object_count"] == 3
    assert requirement["compressed_raw_bytes"] == 300_000_000_000_000
    assert requirement["universe_basis"] == "confirmed_perpetual_membership"
    feasibility = report.storage["gate2_feasibility"]
    assert feasibility["gate2_storage_state"] == "insufficient"
    assert feasibility["shortfall_bytes"] > 0
    assert feasibility["local_available_bytes"] is not None
    assert feasibility["normalized_catalog_bytes"] == "unknown"
    assert feasibility["temporary_high_water_bytes"] == "unknown"
    assert feasibility["operating_reserve_bytes"] == "unknown"
    assert feasibility["total_sufficiency"] == "unknown"
    assert any(item["kind"] == GATE2_STORAGE_BLOCK for item in report.incidents)
    assert report.storage["logical_product_totals_overlap"] is True
    # Storage insufficiency blocks Gate 2; it never relabels a reachable source.
    trades = _row("binance_usdm_bar_1h", report)
    assert trades.authority != "inaccessible"
    assert trades.source_qualification_state == SOURCE_STATE_SAMPLE_PENDING


# --- review-75 source qualification versus temporal coverage --------------------------


def test_object_period_reads_monthly_and_daily_object_keys() -> None:
    assert object_period("x/BTCUSDT-trades-2020-01.zip") == "2020-01"
    assert object_period("x/BTCUSDT-trades-2020-01-05.zip") == "2020-01"
    assert object_period("x/BTCUSDT-trades.zip") is None


def test_family_launch_gap_keeps_official_authority(tmp_path: Path) -> None:
    # The bar product's only acquisition input is the native one-hour kline family, whose
    # first published month is later than the contract's onboarding.
    index = _kline_manifest_index()
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    trades = _row("binance_usdm_bar_1h", report)
    # The kline family simply launched later; the official source keeps its authority.
    assert trades.authority == "official"
    assert trades.source_qualification_state == SOURCE_STATE_TYPED_GAPS
    assert trades.coverage_state == COVERAGE_TYPED_GAPS
    assert "head_gap_family_launch" in trades.coverage_gap_kinds
    assert "BTCUSDT" in trades.typed_gap_symbols
    assert trades.release_blocked is False
    head = next(
        item
        for item in trades.universe_coverage_gaps
        if item["kind"] == "head_gap_family_launch"
    )
    assert head["blocking"] is False
    assert head["explained_by"] == "source_family_launch"
    temporal = report.storage["symbol_temporal_coverage"]["binance_usdm_bar_1h"]["BTCUSDT"]
    assert temporal == {"first": "2020-01", "last": "2020-03", "months": 3}


def test_interior_month_gap_blocks_release_without_withdrawing_authority(
    tmp_path: Path,
) -> None:
    kline_zip = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h")],
        interval_map={"monthly/klines": ["1h"]},
        payload_by_stem={"1h": kline_zip},
        months=("2020-01", "2020-03"),
    )
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    bars = _row("binance_usdm_bar_1h", report)
    # A missing interior month is a real, blocking coverage gap, not a source failure.
    assert bars.authority == "official"
    assert bars.source_qualification_state == SOURCE_STATE_OFFICIAL
    assert bars.coverage_state == COVERAGE_BLOCKING_GAPS
    assert "interior_month_gap" in bars.coverage_gap_kinds
    assert bars.release_blocked is True
    assert "binance_usdm_bar_1h" in report.blocked_products
    gap = next(
        item for item in bars.universe_coverage_gaps if item["kind"] == "interior_month_gap"
    )
    assert gap["missing_months"] == ["2020-02"]


# --- review-75 stable Coinalyze anchors -----------------------------------------------


def test_coinalyze_anchors_must_be_confirmed_perpetuals(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT"),
        coinalyze_transport=_coinalyze_anchor_transport(),
        coinalyze_api_key="sekret",
    )
    assert report.coinalyze["anchor_symbols"] == list(COINALYZE_ANCHOR_SYMBOLS)
    assert report.coinalyze["qualified"] is False
    assert report.coinalyze["unconfirmed_anchors"] == ["ETHUSDT"]
    assert any(item["kind"] == "coinalyze_anchor_unconfirmed" for item in report.incidents)


def test_coinalyze_universe_support_gap_is_reported_separately(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        coinalyze_transport=_coinalyze_anchor_transport(),
        coinalyze_api_key="sekret",
    )
    assert report.coinalyze["qualified"] is True
    assert report.coinalyze["requested_symbols"] == ["BTCUSDT_PERP.A", "ETHUSDT_PERP.A"]
    support = report.coinalyze["universe_support"]
    # Anchor success is not coverage: SOLUSDT is confirmed but unmapped in Coinalyze.
    assert support["supported_symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert support["unmapped_symbols"] == ["SOLUSDT"]
    assert support["universe_size"] == 3
    liquidation = _row("binance_usdm_liquidation_observed_daily", report)
    assert liquidation.authority == "secondary"
    assert liquidation.source_qualification_state == SOURCE_STATE_SECONDARY
    assert liquidation.coverage_state == COVERAGE_TYPED_GAPS
    assert liquidation.official_complete is True
    assert liquidation.release_blocked is False
    assert "SOLUSDT" in liquidation.uncovered_universe_symbols


def test_pre_lock_greedy_plan_is_preserved_before_the_first_lock(tmp_path: Path) -> None:
    legacy = {
        "entries": [{"key": "legacy-key", "action": "download"}],
        "blocked": [],
        "new_download_bytes": 12345,
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "cex002_sample_plan.json").write_text(json.dumps(legacy), encoding="utf-8")
    index = _trades_index(["BTCUSDT"])
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    # The pre-lock greedy plan is evidence of earlier selection and spend; the first lock
    # preserves it instead of overwriting it.
    assert report.plan_lock["plan_version"] == 1
    assert report.plan_lock["legacy_plan_preserved"] is True
    assert json.loads((tmp_path / LEGACY_PLAN_BACKUP_FILENAME).read_text()) == legacy
    lock = SamplePlanLock.load(tmp_path / SAMPLE_PLAN_LOCK_FILENAME)
    assert lock is not None
    assert lock.history[0]["plan"] == legacy
    assert lock.history[0]["inputs"]["source"] == "pre_lock_greedy_plan"


# --- review-76 crash-safe budget accounting -------------------------------------------


def test_interruption_between_checkpoint_and_ledger_keeps_the_charge(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    prefix = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/"
    one_object = int(index.objects[prefix][0].size or 0)
    ledger_path = tmp_path / BUDGET_LEDGER_FILENAME
    ledger = BudgetLedger.bootstrap(
        ledger_path,
        budget_bytes=one_object,
        retained_objects={},
        sample_dir=tmp_path / "raw" / "sha256",
        sidecar_dir=tmp_path / "list_cache",
    )

    def _abort_before_settle(key: str, byte_size: int, **_kwargs: Any) -> None:
        raise _InjectedAbort(key)

    ledger.settle = _abort_before_settle  # type: ignore[method-assign]
    with pytest.raises(_InjectedAbort):
        run_source_qualification(
            store_root=tmp_path,
            index=index,
            current_contracts=_contracts("BTCUSDT"),
            sample_budget_bytes=one_object,
            budget_ledger=ledger,
        )

    # The sample checkpoint was flushed before the crash, and so was the reservation.
    progress = json.loads((tmp_path / "cex002_qualification_progress.json").read_text())
    assert progress["objects"]
    saved = json.loads(ledger_path.read_text())
    assert saved["reservations"]
    assert saved["charges"] == {}
    crashed = BudgetLedger.load(ledger_path, budget_bytes=one_object)
    assert crashed is not None
    # The interrupted download is still charged, so no allowance is restored.
    assert crashed.charged_bytes == one_object
    assert crashed.remaining_bytes == 0

    resumed = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT"),
        sample_budget_bytes=one_object,
    )
    assert resumed.budget["reserved_object_count"] == 0
    assert resumed.budget["settled_object_count"] == 1
    assert resumed.budget["charged_bytes"] == one_object
    assert resumed.budget["cumulative_remaining_bytes"] == 0
    assert resumed.budget["reconciliation"]["settled"] == 1


def test_unprovable_reservation_stays_conservatively_charged(tmp_path: Path) -> None:
    ledger = BudgetLedger(path=tmp_path / BUDGET_LEDGER_FILENAME, budget_bytes=1_000)
    ledger.reserve("data/futures/um/monthly/trades/BTCUSDT/BTCUSDT-trades-2020-01.zip", 400)
    outcome = ledger.reconcile(
        {}, sample_dir=tmp_path / "raw", sidecar_dir=tmp_path / "cache"
    )
    # Nothing proves the bytes were never transferred, so the charge stands.
    assert outcome["settled"] == 0
    assert outcome["unresolved"] == 1
    assert ledger.charged_bytes == 400
    assert ledger.remaining_bytes == 600


# --- review-76 retained contract-metadata authority -----------------------------------


def test_exchange_info_row_missing_identity_fields_fails_closed() -> None:
    with pytest.raises(SourceQualificationError, match="missing required contract identity"):
        parse_exchange_info_rows(
            {
                "timezone": "UTC",
                "serverTime": 1_577_836_800_000,
                "symbols": [{"symbol": "BTCUSDT", "contractType": "PERPETUAL"}],
            }
        )


def test_exchange_info_response_is_retained_content_addressably(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    snapshots = sorted((tmp_path / CONTRACT_SNAPSHOT_DIRNAME).iterdir())
    assert snapshots
    for blob in snapshots:
        assert len(blob.name) == 64
        assert hashlib.sha256(blob.read_bytes()).hexdigest() == blob.name


def test_retained_metadata_fails_closed_when_its_response_is_tampered(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT", "OLDUSDT"])
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT", "OLDUSDT")
    )
    document = json.loads((tmp_path / CONTRACT_METADATA_FILENAME).read_text())
    snapshot = next(iter(document["snapshots"].values()))
    Path(snapshot["content_path"]).write_bytes(b'{"symbols": []}')
    # A valid-JSON edit of the retained response can never manufacture membership.
    with pytest.raises(ResumeIntegrityError, match="not at their content address"):
        run_source_qualification(
            store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
        )


def test_retained_metadata_cannot_claim_an_absent_symbol(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    path = tmp_path / CONTRACT_METADATA_FILENAME
    document = json.loads(path.read_text())
    digest = next(iter(document["snapshots"]))
    document["symbol_snapshot"]["FAKEUSDT"] = digest
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ResumeIntegrityError, match="claims a symbol its response does not"):
        run_source_qualification(
            store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
        )


# --- review-76 verified storage credit and separated scopes ---------------------------


def test_storage_credit_requires_rehashed_and_resproved_evidence(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    feasibility = report.storage["gate2_feasibility"]
    assert feasibility["retained_verified_credit_objects"] >= 1
    assert feasibility["unverified_retained_objects"] == 0
    progress = json.loads((tmp_path / "cex002_qualification_progress.json").read_text())
    key, entry = next(iter(progress["objects"].items()))
    sample_dir = tmp_path / "raw" / "sha256"
    cache = tmp_path / "list_cache"
    assert verify_retained_object(key, entry, sample_dir=sample_dir, sidecar_dir=cache) == int(
        entry["byte_size"]
    )
    Path(entry["provider_checksum_path"]).unlink()
    # Without a re-provable sidecar the row earns no credit at all.
    assert verify_retained_object(key, entry, sample_dir=sample_dir, sidecar_dir=cache) is None


def test_full_union_and_confirmed_universe_totals_are_separate(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT", "ZZZUSDT"])
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    full = report.storage["full_archive_union_totals"]["object_count_exact"]
    confirmed = report.storage["confirmed_universe_totals"]["object_count_exact"]
    # ZZZUSDT is inventoried but unresolved, so it counts in the union and not in scope.
    assert full["binance_usdm_bar_1h"] == 6
    assert confirmed["binance_usdm_bar_1h"] == 3
    row = _row("binance_usdm_bar_1h", report)
    assert row.listed_object_count == 6
    assert row.accepted_universe_object_count == 3
    assert report.storage["confirmed_universe_totals"]["scope"] == report.membership[
        "universe_basis"
    ]


# --- review-76 evidence-based temporal windows ----------------------------------------


def _kline_index(months: Sequence[str] = CONTIGUOUS_MONTHS, **kwargs: Any) -> MemoryObjectIndex:
    return _index_with_family(
        symbols=["AAAUSDT", "BBBUSDT"],
        families=[("monthly/klines", "1h")],
        interval_map={"monthly/klines": ["1h"]},
        payload_by_stem={
            "1h": _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
        },
        months=months,
        **kwargs,
    )


def _drop_object(index: MemoryObjectIndex, symbol: str, month: str) -> None:
    prefix = f"{vision_prefix('monthly', 'klines')}{symbol}/1h/"
    key = f"{prefix}{symbol}-1h-{month}.zip"
    index.objects[prefix] = [obj for obj in index.objects[prefix] if obj.key != key]
    index.bodies.pop(vision_object_url(key), None)
    index.bodies.pop(vision_object_url(f"{key}.CHECKSUM"), None)


def test_unexplained_head_gap_blocks_release(tmp_path: Path) -> None:
    index = _kline_index()
    _drop_object(index, "BBBUSDT", "2020-01")
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("AAAUSDT", "BBBUSDT")
    )
    bars = _row("binance_usdm_bar_1h", report)
    # BBBUSDT onboarded long before the family's first month, so its late start is a gap.
    assert "head_gap_unexplained" in bars.coverage_gap_kinds
    assert bars.authority == "official"
    assert bars.coverage_state == COVERAGE_BLOCKING_GAPS
    assert bars.release_blocked is True


def test_authenticated_pre_listing_head_gap_is_not_blocking(tmp_path: Path) -> None:
    index = _kline_index()
    _drop_object(index, "BBBUSDT", "2020-01")
    contracts = MemoryCurrentContractSource(
        {
            "timezone": "UTC",
            "serverTime": 1577836800000,
            "symbols": [
                _perpetual_row("AAAUSDT"),
                # Onboarded in 2020-02: there is no earlier history to be missing.
                _perpetual_row("BBBUSDT", onboard_ms=1_580_515_200_000),
            ],
        }
    )
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=contracts
    )
    bars = _row("binance_usdm_bar_1h", report)
    assert "head_gap_pre_listing" in bars.coverage_gap_kinds
    assert "head_gap_unexplained" not in bars.coverage_gap_kinds
    assert bars.coverage_state == COVERAGE_TYPED_GAPS
    assert bars.release_blocked is False
    head = next(
        item for item in bars.universe_coverage_gaps if item["kind"] == "head_gap_pre_listing"
    )
    assert head["blocking"] is False
    assert head["explained_by"] == "authenticated_onboard_date"


def test_currently_listed_missing_recent_tail_blocks_release(tmp_path: Path) -> None:
    index = _kline_index()
    _drop_object(index, "AAAUSDT", "2020-03")
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("AAAUSDT", "BBBUSDT")
    )
    bars = _row("binance_usdm_bar_1h", report)
    # The family published 2020-03 for another symbol, so a listed contract is missing it.
    assert "tail_gap_missing_recent" in bars.coverage_gap_kinds
    assert "AAAUSDT" in bars.uncovered_universe_symbols
    assert bars.release_blocked is True


def test_authenticated_post_close_tail_is_not_blocking(tmp_path: Path) -> None:
    index = _kline_index()
    _drop_object(index, "AAAUSDT", "2020-03")
    contracts = MemoryCurrentContractSource(
        {
            "timezone": "UTC",
            "serverTime": 1577836800000,
            "symbols": [
                # Settled during 2020-02; nothing later can exist for it.
                _perpetual_row("AAAUSDT", delivery_ms=1_582_934_400_000, status="SETTLING"),
                _perpetual_row("BBBUSDT"),
            ],
        }
    )
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=contracts
    )
    bars = _row("binance_usdm_bar_1h", report)
    assert "tail_gap_post_close" in bars.coverage_gap_kinds
    assert "tail_gap_missing_recent" not in bars.coverage_gap_kinds
    tail = next(
        item for item in bars.universe_coverage_gaps if item["kind"] == "tail_gap_post_close"
    )
    assert tail["blocking"] is False
    assert tail["explained_by"] == "authenticated_close_or_delivery"


def test_unknown_delisting_tail_stays_blocking(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["AAAUSDT", "BBBUSDT"],
        families=[("monthly/klines", "1h"), ("monthly/fundingRate", "fundingRate")],
        interval_map={"monthly/klines": ["1h"]},
        payload_by_stem={
            "1h": _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes()),
            "fundingRate": _zip_bytes("f.csv", (FIXTURES / "headed_funding.csv").read_bytes()),
        },
        months=CONTIGUOUS_MONTHS,
    )
    _drop_object(index, "AAAUSDT", "2020-03")
    # AAAUSDT is proven perpetual by realized funding but has no lifecycle evidence.
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BBBUSDT")
    )
    bars = _row("binance_usdm_bar_1h", report)
    assert "tail_gap_unknown_close" in bars.coverage_gap_kinds
    assert bars.release_blocked is True
    tail = next(
        item for item in bars.universe_coverage_gaps if item["kind"] == "tail_gap_unknown_close"
    )
    assert tail["symbol"] == "AAAUSDT"
    assert tail["close_period"] is None


# --- review-76 Coinalyze native identity and complete gap evidence --------------------


def test_coinalyze_refuses_a_market_whose_native_identity_disagrees() -> None:
    markets = _load_json("coinalyze_future_markets.json")
    assert isinstance(markets, list)
    markets[0]["symbol"] = "BTCUSDT_PERP.B"
    payloads = {
        "/future-markets": json.dumps(markets).encode("utf-8"),
        **{
            path: (FIXTURES / name).read_bytes()
            for path, name in COINALYZE_ANCHOR_FIXTURE_FILES.items()
            if path != "/future-markets"
        },
    }
    client = CoinalyzeClient(
        MemoryCoinalyzeTransport(raw_payloads=payloads), api_key="sekret"
    )
    with pytest.raises(SourceQualificationError, match="disagrees with its native identity"):
        client.qualify_binance_daily(
            anchor_symbols=["BTCUSDT", "ETHUSDT"],
            universe_symbols=["BTCUSDT", "ETHUSDT"],
            from_ts=1_577_836_800,
            to_ts=1_609_459_200,
        )


def test_coinalyze_unmapped_universe_gaps_are_not_truncated(tmp_path: Path) -> None:
    extra = [f"SYM{index:03d}USDT" for index in range(210)]
    index = _trades_index(["BTCUSDT", "ETHUSDT"])
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT", "ETHUSDT", *extra),
        coinalyze_transport=_coinalyze_anchor_transport(),
        coinalyze_api_key="sekret",
    )
    assert report.coinalyze["qualified"] is True
    support = report.coinalyze["universe_support"]
    assert support["unmapped_count"] == 210
    liquidation = _row("binance_usdm_liquidation_observed_daily", report)
    # Every unmapped confirmed perpetual is retained as product gap evidence.
    assert len(liquidation.universe_coverage_gaps) == 210
    assert len(liquidation.uncovered_universe_symbols) == 210
    assert liquidation.release_blocked is False


# --- review-77 inseparable current-contract authority ---------------------------------


class _SplitContractSource:
    """Retains one official universe while classifying from a different mapping."""

    def __init__(self, retained: Mapping[str, Any], claimed: Mapping[str, Any]) -> None:
        self._retained = retained
        self._claimed = claimed

    def fetch_exchange_info(self) -> ExchangeInfoResponse:
        raw = json.dumps(dict(self._retained), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return ExchangeInfoResponse(
            endpoint=OFFICIAL_INCREMENTAL_ENDPOINTS["exchangeInfo"],
            payload=dict(self._claimed),
            raw_bytes=raw,
            sha256=hashlib.sha256(raw).hexdigest(),
            byte_size=len(raw),
            retrieval_time="2026-08-20T00:00:00+00:00",
            content_path="",
        )


def test_contract_payload_must_be_what_the_retained_bytes_decode_to(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT", "ZZZUSDT"])
    source = _SplitContractSource(
        _exchange_info("BTCUSDT"), _exchange_info("BTCUSDT", "ZZZUSDT")
    )
    # Retaining one universe and classifying another is an authority substitution.
    with pytest.raises(ResumeIntegrityError, match="not what its retained bytes decode to"):
        run_source_qualification(
            store_root=tmp_path, index=index, current_contracts=source
        )


def test_contract_response_identity_is_checked_before_reliance() -> None:
    payload = _exchange_info("BTCUSDT")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()

    def _response(**overrides: Any) -> ExchangeInfoResponse:
        fields: dict[str, Any] = {
            "endpoint": OFFICIAL_INCREMENTAL_ENDPOINTS["exchangeInfo"],
            "payload": json.loads(raw.decode("utf-8")),
            "raw_bytes": raw,
            "sha256": digest,
            "byte_size": len(raw),
            "retrieval_time": "2026-08-20T00:00:00+00:00",
            "content_path": "",
        }
        fields.update(overrides)
        return ExchangeInfoResponse(**fields)

    assert validate_exchange_info_response(_response()) == json.loads(raw.decode("utf-8"))
    with pytest.raises(SourceQualificationError, match="not the official exchangeInfo endpoint"):
        validate_exchange_info_response(_response(endpoint="https://example.invalid/info"))
    with pytest.raises(ResumeIntegrityError, match="byte count disagrees"):
        validate_exchange_info_response(_response(byte_size=len(raw) + 1))
    with pytest.raises(ResumeIntegrityError, match="digest disagrees"):
        validate_exchange_info_response(_response(sha256="a" * 64))
    with pytest.raises(SourceQualificationError, match="no parseable retrieval time"):
        validate_exchange_info_response(_response(retrieval_time=""))
    with pytest.raises(ResumeIntegrityError, match="not its retained content address"):
        validate_exchange_info_response(_response(content_path="/nonexistent/blob"))


def test_present_but_empty_contract_identity_fails_closed() -> None:
    payload = _exchange_info("BTCUSDT")
    payload["symbols"][0]["underlyingType"] = ""
    with pytest.raises(SourceQualificationError, match="empty contract identity field"):
        parse_exchange_info_rows(payload)
    payload = _exchange_info("BTCUSDT")
    payload["symbols"][0]["deliveryDate"] = None
    with pytest.raises(SourceQualificationError, match="invalid contract lifecycle boundary"):
        parse_exchange_info_rows(payload)
    payload = _exchange_info("BTCUSDT")
    payload.pop("serverTime")
    with pytest.raises(SourceQualificationError, match="no authenticated serverTime"):
        parse_exchange_info_rows(payload)


def _row_of(symbol: str, **overrides: Any) -> dict[str, Any]:
    payload = _exchange_info(symbol)
    payload["symbols"][0].update(overrides)
    return parse_exchange_info_rows(payload)[symbol]


def test_only_positively_supported_crypto_semantics_are_confirmed() -> None:
    assert is_confirmed_perpetual_row(_row_of("BTCUSDT"))
    assert contract_semantics_state(_row_of("BTCUSDT")) == SEMANTICS_SUPPORTED
    # "Not TradFi" is not evidence of crypto; an unknown enum stays unproved.
    unknown_underlying = _row_of("BTCUSDT", underlyingType="UNKNOWN")
    assert contract_semantics_state(unknown_underlying) == SEMANTICS_UNKNOWN_UNDERLYING
    assert not is_confirmed_perpetual_row(unknown_underlying)
    unknown_status = _row_of("BTCUSDT", status="SOMETHING_NEW")
    assert contract_semantics_state(unknown_status) == SEMANTICS_UNKNOWN_STATUS
    assert not is_confirmed_perpetual_row(unknown_status)
    incoherent_pair = _row_of("BTCUSDT", pair="ETHUSDT")
    assert contract_semantics_state(incoherent_pair) == SEMANTICS_INCOHERENT_IDENTITY
    assert not is_confirmed_perpetual_row(incoherent_pair)
    incoherent_margin = _row_of("BTCUSDT", marginAsset="BUSD")
    assert contract_semantics_state(incoherent_margin) == SEMANTICS_INCOHERENT_IDENTITY
    assert not is_confirmed_perpetual_row(incoherent_margin)


def test_unsupported_contract_semantics_block_membership(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    payload = _exchange_info("BTCUSDT")
    payload["symbols"][0]["underlyingType"] = "UNKNOWN"
    payload["symbols"].append(_perpetual_row("ETHUSDT"))
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=MemoryCurrentContractSource(payload),
    )
    classes = report.membership["classes"]
    assert classes[MEMBERSHIP_UNSUPPORTED_SEMANTICS] == ["BTCUSDT"]
    assert "BTCUSDT" not in report.accepted_universe
    assert report.membership["resolved"] is False
    assert "BTCUSDT" in report.membership["unresolved_symbols"]


def test_duplicate_native_contract_symbols_fail_closed() -> None:
    payload = _exchange_info("BTCUSDT")
    payload["symbols"].append(_perpetual_row("BTCUSDT", status="SETTLING"))
    with pytest.raises(SourceQualificationError, match="duplicate native contract symbols"):
        parse_exchange_info_rows(payload)


def test_close_boundary_is_the_persisted_first_closed_observation(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT", "OLDUSDT"])
    first_close = 1_583_020_800_000
    settling = {
        "timezone": "UTC",
        "serverTime": first_close,
        "symbols": [_perpetual_row("BTCUSDT"), _perpetual_row("OLDUSDT", status="SETTLING")],
    }
    run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=MemoryCurrentContractSource(settling),
    )
    store = OfficialContractMetadataStore.load(
        tmp_path / CONTRACT_METADATA_FILENAME,
        snapshot_dir=tmp_path / CONTRACT_SNAPSHOT_DIRNAME,
    )
    assert store.closed_observations["OLDUSDT"]["server_time_ms"] == first_close

    # A later fetch reports a new response time; the boundary must not move with it.
    later = {
        "timezone": "UTC",
        "serverTime": first_close + 90 * 86_400_000,
        "symbols": [_perpetual_row("BTCUSDT"), _perpetual_row("OLDUSDT", status="SETTLING")],
    }
    rows = store.enrich(parse_exchange_info_rows(later))
    assert exchange_info_server_time_ms(later) != first_close
    assert contract_close_ms(rows["OLDUSDT"]) == first_close
    assert contract_close_ms(rows["BTCUSDT"]) is None


def test_retained_metadata_boundary_ignores_a_tampered_observation_field(
    tmp_path: Path,
) -> None:
    index = _trades_index(["BTCUSDT", "OLDUSDT"])
    settling = {
        "timezone": "UTC",
        "serverTime": 1_583_020_800_000,
        "symbols": [
            _perpetual_row("BTCUSDT"),
            _perpetual_row("OLDUSDT", status="SETTLING"),
        ],
    }
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=MemoryCurrentContractSource(settling)
    )
    path = tmp_path / CONTRACT_METADATA_FILENAME
    document = json.loads(path.read_text())
    for snapshot in document["snapshots"].values():
        snapshot["observed_at"] = "2030-06-01T00:00:00+00:00"
    path.write_text(json.dumps(document), encoding="utf-8")

    store = OfficialContractMetadataStore.load(
        path, snapshot_dir=tmp_path / CONTRACT_SNAPSHOT_DIRNAME
    )
    rows = store.historical_rows()
    # The editable observation field is carried for audit but decides nothing; the close
    # boundary comes from the authenticated response's own serverTime.
    assert rows["OLDUSDT"]["observed_at"] == "2030-06-01T00:00:00+00:00"
    assert rows["OLDUSDT"]["server_time_ms"] == 1_583_020_800_000
    assert contract_close_ms(rows["OLDUSDT"]) == 1_583_020_800_000


# --- review-77 plan bound to re-proved authority --------------------------------------


def test_only_reproved_retained_objects_are_frozen_into_the_plan(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    assert report.resume["unverified_retained_sample_keys"] == 0
    progress = json.loads((tmp_path / "cex002_qualification_progress.json").read_text())
    key, entry = next(iter(progress["objects"].items()))
    sample_dir = tmp_path / "raw" / "sha256"
    cache = tmp_path / "list_cache"
    proved = retained_evidence_snapshot(
        [key], progress["objects"], sample_dir=sample_dir, sidecar_dir=cache
    )
    assert proved[key][0] == entry["sha256"]
    assert proved[key][2] == int(entry["byte_size"])

    Path(entry["provider_checksum_path"]).unlink()
    unproved = retained_evidence_snapshot(
        [key], progress["objects"], sample_dir=sample_dir, sidecar_dir=cache
    )
    # A checkpoint claim alone is never frozen as authority, and the digest moves.
    assert unproved[key] == ["", "", 0]
    assert retained_evidence_digest(unproved) != retained_evidence_digest(proved)


def test_listing_authority_manifest_binds_request_identity_to_raw_digests(
    tmp_path: Path,
) -> None:
    store, _checkpoint_path, _pages = _listing_store_with_two_prefixes(tmp_path)
    manifest = listing_authority_manifest(store)
    assert manifest
    for item in manifest:
        assert len(item["response_sha256"]) == 64
        assert item["request"]["list_type"] == "2"
        assert item["request_key"]
    before = listing_authority_digest(store)
    key = next(iter(store.entries))
    store.entries[key]["response_sha256"] = "b" * 64
    # Substituting the retained response behind a request changes the bound authority.
    assert listing_authority_digest(store) != before
    assert listing_authority_digest(None) == listing_authority_digest(
        ListingCheckpointStore(path=tmp_path / "empty.json", cache_dir=tmp_path)
    )


def test_membership_digest_covers_complete_contract_evidence() -> None:
    def _digest(payload: Mapping[str, Any], sha: str) -> str:
        rows = parse_exchange_info_rows(payload)
        return membership_evidence_digest(
            classify_membership(
                discovered=["BTCUSDT"],
                current_rows=rows,
                historical_rows={},
                funding_evidence={},
                current_response_sha256=sha,
            )
        )

    base = _exchange_info("BTCUSDT")
    baseline = _digest(base, "a" * 64)
    altered_pair = _exchange_info("BTCUSDT")
    altered_pair["symbols"][0]["pair"] = "BTCUSD_ALT"
    altered_margin = _exchange_info("BTCUSDT")
    altered_margin["symbols"][0]["marginAsset"] = "BUSD"
    altered_onboard = _exchange_info("BTCUSDT")
    altered_onboard["symbols"][0]["onboardDate"] = DEFAULT_ONBOARD_MS + 86_400_000
    # Pair, margin and lifecycle semantics all bind the plan.
    assert _digest(altered_pair, "a" * 64) != baseline
    assert _digest(altered_margin, "a" * 64) != baseline
    assert _digest(altered_onboard, "a" * 64) != baseline
    # Raw-response churn over identical contract rows must not.
    assert _digest(base, "c" * 64) == baseline


def test_canonical_contract_row_reports_every_identity_field() -> None:
    rows = parse_exchange_info_rows(_exchange_info("BTCUSDT"))
    canonical = canonical_contract_row(rows["BTCUSDT"])
    assert set(canonical) == {
        "symbol",
        "pair",
        "contract_type",
        "status",
        "underlying_type",
        "base_asset",
        "quote_asset",
        "margin_asset",
        "onboard_ms",
        "delivery_ms",
        "closed_observed_ms",
        "semantics_state",
    }
    assert canonical["base_asset"] == "BTC"
    assert canonical["margin_asset"] == "USDT"
    assert canonical["semantics_state"] == SEMANTICS_SUPPORTED
    # Response-wide volatility lives in provenance, never in canonical semantics.
    provenance = contract_provenance({**rows["BTCUSDT"], "response_sha256": "a" * 64})
    assert provenance["server_time_ms"] == exchange_info_server_time_ms(_exchange_info("BTCUSDT"))
    assert provenance["response_sha256"] == "a" * 64


# --- review-77 durable ledger validation ----------------------------------------------


def test_negative_ledger_amount_fails_before_any_download(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    ledger_path = tmp_path / BUDGET_LEDGER_FILENAME
    document = json.loads(ledger_path.read_text())
    key = next(iter(document["charges"]))
    document["charges"][key]["transferred_bytes"] = -5
    ledger_path.write_text(json.dumps(document), encoding="utf-8")

    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    with pytest.raises(ResumeIntegrityError, match="not a valid size"):
        run_source_qualification(
            store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
        )
    # An allowance-restoring ledger is an integrity failure, never spend.
    assert fetched == []


def test_ledger_written_for_another_budget_fails_closed(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    prefix = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/"
    one_object = int(index.objects[prefix][0].size or 0)
    run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT"),
        sample_budget_bytes=one_object,
    )
    with pytest.raises(ResumeIntegrityError, match="different Gate 1 budget"):
        run_source_qualification(
            store_root=tmp_path,
            index=index,
            current_contracts=_contracts("BTCUSDT"),
            sample_budget_bytes=one_object * 2,
        )


def _charge(planned: int, transferred: int, *, disposition: str = LEDGER_TRANSFERRED) -> dict:
    return {
        "planned_bytes": planned,
        "transferred_bytes": transferred,
        "disposition": disposition,
        "sha256": "a" * 64,
    }


def test_ledger_rejects_overlapping_and_oversized_amounts(tmp_path: Path) -> None:
    ledger = BudgetLedger(
        path=tmp_path / BUDGET_LEDGER_FILENAME,
        budget_bytes=1_000,
        charges={"k": _charge(10, 10)},
        reservations={"k": {"planned_bytes": 10}},
    )
    with pytest.raises(ResumeIntegrityError, match="not disjoint"):
        ledger.validate()
    oversized = BudgetLedger(
        path=tmp_path / BUDGET_LEDGER_FILENAME,
        budget_bytes=100,
        charges={"k": _charge(101, 101)},
    )
    with pytest.raises(ResumeIntegrityError, match="exceeds the Gate 1 budget"):
        oversized.validate()
    naked_zero = BudgetLedger(
        path=tmp_path / BUDGET_LEDGER_FILENAME,
        budget_bytes=100,
        charges={"k": _charge(10, 0)},
    )
    # A zero charge without an explicit no-transfer disposition is indistinguishable
    # from an allowance-restoring edit.
    with pytest.raises(ResumeIntegrityError, match="no no-transfer disposition"):
        naked_zero.validate()
    above_floor = BudgetLedger(
        path=tmp_path / BUDGET_LEDGER_FILENAME,
        budget_bytes=100,
        charges={"k": _charge(10, 11)},
    )
    with pytest.raises(ResumeIntegrityError, match="exceeds its planned floor"):
        above_floor.validate()


# --- review-77 Coinalyze identity for every market ------------------------------------


def _markets_transport(markets: list[dict[str, Any]]) -> MemoryCoinalyzeTransport:
    payloads = {
        "/future-markets": json.dumps(markets).encode("utf-8"),
        **{
            path: (FIXTURES / name).read_bytes()
            for path, name in COINALYZE_ANCHOR_FIXTURE_FILES.items()
            if path != "/future-markets"
        },
    }
    return MemoryCoinalyzeTransport(raw_payloads=payloads)


def test_coinalyze_refuses_a_non_anchor_identity_mismatch() -> None:
    markets = _load_json("coinalyze_future_markets.json")
    assert isinstance(markets, list)
    non_anchor = next(row for row in markets if row["symbol_on_exchange"] == "AAVEUSDT")
    non_anchor["symbol"] = "AAVEUSDT_PERP.X"
    client = CoinalyzeClient(_markets_transport(markets), api_key="sekret")
    # A non-anchor row feeds the support map, so it needs the same proved identity.
    with pytest.raises(SourceQualificationError, match="disagrees with its native identity"):
        client.qualify_binance_daily(
            anchor_symbols=["BTCUSDT", "ETHUSDT"],
            universe_symbols=["BTCUSDT", "ETHUSDT", "AAVEUSDT"],
            from_ts=1_577_836_800,
            to_ts=1_609_459_200,
        )


def test_coinalyze_refuses_duplicate_native_identities() -> None:
    markets = _load_json("coinalyze_future_markets.json")
    assert isinstance(markets, list)
    duplicate = dict(next(row for row in markets if row["symbol_on_exchange"] == "BTCUSDT"))
    markets.append(duplicate)
    client = CoinalyzeClient(_markets_transport(markets), api_key="sekret")
    with pytest.raises(SourceQualificationError, match="duplicate Binance perpetual native"):
        client.qualify_binance_daily(
            anchor_symbols=["BTCUSDT", "ETHUSDT"],
            universe_symbols=["BTCUSDT", "ETHUSDT"],
            from_ts=1_577_836_800,
            to_ts=1_609_459_200,
        )


# --- review-78 stable authority across live response churn ----------------------------


def test_response_time_churn_replays_one_plan_and_keeps_identity(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    rows = [_perpetual_row("BTCUSDT")]
    first = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=MemoryCurrentContractSource(
            {"timezone": "UTC", "serverTime": 1_577_836_800_000, "symbols": rows}
        ),
    )
    # A live exchangeInfo fetch always carries a new serverTime, so the raw response
    # digest changes even when every contract row is identical.
    second = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=MemoryCurrentContractSource(
            {"timezone": "UTC", "serverTime": 1_600_000_000_000, "symbols": rows}
        ),
    )
    assert first.plan_lock["plan_version"] == 1
    assert second.plan_lock["plan_version"] == 1
    assert [entry["key"] for entry in second.sample_plan["entries"]] == [
        entry["key"] for entry in first.sample_plan["entries"]
    ]
    first_evidence = first.membership["classifications"][0]["evidence"][0]
    second_evidence = second.membership["classifications"][0]["evidence"][0]
    # Provenance is retained and validated on every run, but binds neither the plan nor
    # the semantic identity.
    assert first_evidence["response_sha256"] != second_evidence["response_sha256"]
    assert first_evidence["server_time_ms"] != second_evidence["server_time_ms"]
    assert identity_bytes(first) == identity_bytes(second)


def test_changed_contract_rows_still_block_before_download(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    changed = {
        "timezone": "UTC",
        "serverTime": 1_600_000_000_000,
        "symbols": [_perpetual_row("BTCUSDT", status="SETTLING")],
    }
    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    with pytest.raises(ResumeIntegrityError, match="locked Gate 1 plan inputs changed") as err:
        run_source_qualification(
            store_root=tmp_path,
            index=index,
            current_contracts=MemoryCurrentContractSource(changed),
        )
    # A material lifecycle/status change is authority movement and must fail closed.
    assert "membership_digest" in err.value.context["changed"]
    assert fetched == []


def _metadata_artifact_identity(store: Path) -> tuple[bytes, tuple[tuple[str, str], ...]]:
    """Exact bytes of the durable metadata checkpoint and content-addressed snapshots."""
    meta = store / CONTRACT_METADATA_FILENAME
    meta_bytes = meta.read_bytes() if meta.is_file() else b""
    snap_dir = store / CONTRACT_SNAPSHOT_DIRNAME
    snapshots: list[tuple[str, str]] = []
    if snap_dir.is_dir():
        for path in sorted(item for item in snap_dir.iterdir() if item.is_file()):
            snapshots.append((path.name, hashlib.sha256(path.read_bytes()).hexdigest()))
    return meta_bytes, tuple(snapshots)


def test_rejected_live_authority_does_not_poison_a_later_resume(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    rows = [_perpetual_row("BTCUSDT")]
    first = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=MemoryCurrentContractSource(
            {"timezone": "UTC", "serverTime": 1_577_836_800_000, "symbols": rows}
        ),
    )
    before_meta, before_snapshots = _metadata_artifact_identity(tmp_path)

    settling = {
        "timezone": "UTC",
        "serverTime": 1_600_000_000_000,
        "symbols": [_perpetual_row("BTCUSDT", status="SETTLING")],
    }
    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    with pytest.raises(ResumeIntegrityError, match="locked Gate 1 plan inputs changed"):
        run_source_qualification(
            store_root=tmp_path,
            index=index,
            current_contracts=MemoryCurrentContractSource(settling),
        )
    index.fetch_bytes = real_fetch  # type: ignore[method-assign]
    assert fetched == []
    after_meta, after_snapshots = _metadata_artifact_identity(tmp_path)
    # The rejected closed-status response must not change either durable artifact.
    assert after_meta == before_meta
    assert after_snapshots == before_snapshots

    resumed = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=MemoryCurrentContractSource(
            {"timezone": "UTC", "serverTime": 1_650_000_000_000, "symbols": rows}
        ),
    )
    assert resumed.plan_lock["plan_version"] == 1
    assert [entry["key"] for entry in resumed.sample_plan["entries"]] == [
        entry["key"] for entry in first.sample_plan["entries"]
    ]
    assert identity_bytes(first) == identity_bytes(resumed)
    store = OfficialContractMetadataStore.load(
        tmp_path / CONTRACT_METADATA_FILENAME,
        snapshot_dir=tmp_path / CONTRACT_SNAPSHOT_DIRNAME,
    )
    assert "BTCUSDT" not in store.closed_observations


# --- review-78 ledger transition evidence ---------------------------------------------


def _run_once_for_ledger(tmp_path: Path) -> tuple[MemoryObjectIndex, Path]:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    return index, tmp_path / BUDGET_LEDGER_FILENAME


def _rerun_expecting(
    index: MemoryObjectIndex, tmp_path: Path, message: str
) -> None:
    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    with pytest.raises(ResumeIntegrityError, match=message):
        run_source_qualification(
            store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
        )
    index.fetch_bytes = real_fetch  # type: ignore[method-assign]
    assert fetched == []


def test_reservation_reduced_to_zero_fails_before_download(tmp_path: Path) -> None:
    index, ledger_path = _run_once_for_ledger(tmp_path)
    document = json.loads(ledger_path.read_text())
    key = next(iter(document["charges"]))
    # Move a settled charge back to a zero-size reservation: a valid-JSON edit that would
    # otherwise restore its allowance.
    document["reservations"][key] = {"planned_bytes": 0}
    document["charges"].pop(key)
    ledger_path.write_text(json.dumps(document), encoding="utf-8")
    _rerun_expecting(index, tmp_path, "not a valid size")


def test_settled_charge_reduced_to_a_smaller_value_fails_before_download(
    tmp_path: Path,
) -> None:
    index, ledger_path = _run_once_for_ledger(tmp_path)
    document = json.loads(ledger_path.read_text())
    key = next(
        name
        for name, record in document["charges"].items()
        if record["disposition"] == LEDGER_TRANSFERRED and record["transferred_bytes"] > 1
    )
    document["charges"][key]["transferred_bytes"] = 1
    ledger_path.write_text(json.dumps(document), encoding="utf-8")
    # The independent counts/totals no longer agree with the entries.
    _rerun_expecting(index, tmp_path, "integrity summary disagrees")


def test_settled_charge_is_reconciled_against_rehashed_evidence(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    ledger = BudgetLedger.load(
        tmp_path / BUDGET_LEDGER_FILENAME, budget_bytes=GATE1_NEW_DOWNLOAD_BUDGET_BYTES
    )
    assert ledger is not None
    progress = json.loads((tmp_path / "cex002_qualification_progress.json").read_text())
    sample_dir = tmp_path / "raw" / "sha256"
    cache = tmp_path / "list_cache"
    outcome = ledger.reconcile(
        progress["objects"], sample_dir=sample_dir, sidecar_dir=cache
    )
    assert outcome["reproved"] >= 1
    assert outcome["unresolved"] == 0

    key = next(
        name
        for name, record in ledger.charges.items()
        if record["disposition"] == LEDGER_TRANSFERRED
    )
    ledger.charges[key]["transferred_bytes"] = 1
    # Even a self-consistent edit disagrees with the rehashed retained object.
    with pytest.raises(ResumeIntegrityError, match="disagrees with the rehashed retained"):
        ledger.reconcile(progress["objects"], sample_dir=sample_dir, sidecar_dir=cache)


def test_zero_cost_reuse_carries_an_explicit_no_transfer_disposition(
    tmp_path: Path,
) -> None:
    index = _trades_index(["BTCUSDT"])
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    document = json.loads((tmp_path / BUDGET_LEDGER_FILENAME).read_text())
    dispositions = {record["disposition"] for record in document["charges"].values()}
    # These synthetic objects share one payload, so the aliases are content-address
    # reuses that transferred nothing and say so.
    assert dispositions == {LEDGER_TRANSFERRED, LEDGER_NO_TRANSFER}
    assert report.budget["no_transfer_object_count"] >= 1
    for record in document["charges"].values():
        assert record["planned_bytes"] > 0
        assert len(record["sha256"]) == 64
        if record["disposition"] == LEDGER_NO_TRANSFER:
            assert record["transferred_bytes"] == 0
    assert report.budget["integrity"]["charge_count"] == len(document["charges"])


def test_content_address_reuse_skips_raw_fetch_and_records_no_transfer(
    tmp_path: Path,
) -> None:
    index = _trades_index(["BTCUSDT"])
    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    document = json.loads((tmp_path / BUDGET_LEDGER_FILENAME).read_text())
    charges = document["charges"]
    transferred_keys = [
        key
        for key, record in charges.items()
        if record["disposition"] == LEDGER_TRANSFERRED
    ]
    reused_keys = [
        key
        for key, record in charges.items()
        if record["disposition"] == LEDGER_NO_TRANSFER
    ]
    assert transferred_keys
    assert reused_keys
    for key in transferred_keys:
        assert vision_object_url(key) in fetched
        assert charges[key]["transferred_bytes"] == charges[key]["planned_bytes"]
    for key in reused_keys:
        # Sidecar may be fetched; the raw object must not be, and the ledger says so.
        assert vision_object_url(key) not in fetched
        assert charges[key]["transferred_bytes"] == 0
    assert report.budget["no_transfer_object_count"] == len(reused_keys)


def test_missing_destination_raw_fetch_is_recorded_as_a_transfer(
    tmp_path: Path,
) -> None:
    index = _trades_index(["BTCUSDT"], payload_for_key=_distinct_object_payload)
    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    document = json.loads((tmp_path / BUDGET_LEDGER_FILENAME).read_text())
    charges = document["charges"]
    assert charges
    assert all(record["disposition"] == LEDGER_TRANSFERRED for record in charges.values())
    assert report.budget["no_transfer_object_count"] == 0
    for key, record in charges.items():
        assert vision_object_url(key) in fetched
        assert record["transferred_bytes"] == record["planned_bytes"] > 0


# --- review-89 stable storage identity and already-suffixed Coinalyze natives ---------


def test_storage_incident_identity_is_stable_across_local_capacity_churn(
    tmp_path: Path,
) -> None:
    from cryptofactors.acquisition import binance_usdm_harmonic_qualification as module

    kline_zip = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h")],
        interval_map={"monthly/klines": ["1h"]},
        payload_by_stem={"1h": kline_zip},
        months=CONTIGUOUS_MONTHS,
    )
    for prefix in list(index.objects):
        index.objects[prefix] = [
            ListingObject(key=obj.key, size=100_000_000_000_000)
            for obj in index.objects[prefix]
        ]
    real_available = module.available_bytes
    first_capacity = 10_000_000_000
    second_capacity = first_capacity + 75_083_776
    try:
        module.available_bytes = lambda _path: first_capacity  # type: ignore[method-assign]
        first = run_source_qualification(
            store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
        )
        module.available_bytes = lambda _path: second_capacity  # type: ignore[method-assign]
        second = run_source_qualification(
            store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
        )
    finally:
        module.available_bytes = real_available  # type: ignore[method-assign]

    first_feas = first.storage["gate2_feasibility"]
    second_feas = second.storage["gate2_feasibility"]
    assert first_feas["local_available_bytes"] == first_capacity
    assert second_feas["local_available_bytes"] == second_capacity
    assert first_feas["shortfall_bytes"] != second_feas["shortfall_bytes"]
    assert first_feas["gate2_storage_state"] == "insufficient"
    assert second_feas["gate2_storage_state"] == "insufficient"
    first_incidents = [item for item in first.incidents if item["kind"] == GATE2_STORAGE_BLOCK]
    second_incidents = [item for item in second.incidents if item["kind"] == GATE2_STORAGE_BLOCK]
    assert first_incidents
    assert first_incidents == second_incidents
    assert {item["note"] for item in first_incidents} == {GATE2_STORAGE_INCIDENT_NOTE}
    assert str(first_feas["shortfall_bytes"]) not in GATE2_STORAGE_INCIDENT_NOTE
    assert str(second_feas["shortfall_bytes"]) not in GATE2_STORAGE_INCIDENT_NOTE
    assert identity_bytes(first) == identity_bytes(second)


def test_coinalyze_perp_symbol_maps_unsuffixed_and_already_suffixed_natives() -> None:
    assert coinalyze_perp_symbol("BTCUSDT") == "BTCUSDT_PERP.A"
    assert coinalyze_perp_symbol("AAVEUSD_PERP") == "AAVEUSD_PERP.A"


def test_coinalyze_accepts_already_suffixed_native_provider_identity() -> None:
    markets = _load_json("coinalyze_future_markets.json")
    assert isinstance(markets, list)
    markets.append(
        {
            "symbol": "AAVEUSD_PERP.A",
            "exchange": "A",
            "symbol_on_exchange": "AAVEUSD_PERP",
            "base_asset": "AAVE",
            "quote_asset": "USD",
            "is_perpetual": True,
            "margined": "STABLE",
            "expire_at": None,
            "oi_lq_vol_denominated_in": "BASE_ASSET",
        }
    )
    client = CoinalyzeClient(_markets_transport(markets), api_key="sekret")
    evidence = client.qualify_binance_daily(
        anchor_symbols=["BTCUSDT", "ETHUSDT"],
        universe_symbols=["BTCUSDT", "ETHUSDT", "AAVEUSD_PERP"],
        from_ts=1_577_836_800,
        to_ts=1_609_459_200,
    )
    assert "AAVEUSD_PERP" in evidence["universe_support"]["supported_symbols"]
    assert coinalyze_perp_symbol("AAVEUSD_PERP") == "AAVEUSD_PERP.A"


def test_coinalyze_rejects_mismatched_provider_for_already_suffixed_native() -> None:
    markets = _load_json("coinalyze_future_markets.json")
    assert isinstance(markets, list)
    markets.append(
        {
            "symbol": "AAVEUSD_PERP_PERP.A",
            "exchange": "A",
            "symbol_on_exchange": "AAVEUSD_PERP",
            "base_asset": "AAVE",
            "quote_asset": "USD",
            "is_perpetual": True,
            "margined": "STABLE",
            "expire_at": None,
            "oi_lq_vol_denominated_in": "BASE_ASSET",
        }
    )
    client = CoinalyzeClient(_markets_transport(markets), api_key="sekret")
    with pytest.raises(SourceQualificationError, match="disagrees with its native identity") as err:
        client.qualify_binance_daily(
            anchor_symbols=["BTCUSDT", "ETHUSDT"],
            universe_symbols=["BTCUSDT", "ETHUSDT", "AAVEUSD_PERP"],
            from_ts=1_577_836_800,
            to_ts=1_609_459_200,
        )
    assert err.value.context["native"] == "AAVEUSD_PERP"
    assert err.value.context["provider_symbol"] == "AAVEUSD_PERP_PERP.A"
    assert err.value.context["expected"] == "AAVEUSD_PERP.A"


# --- review-98 selected Harmonic release contract -------------------------------------


def test_required_products_are_the_amended_harmonic_set() -> None:
    assert "binance_usdm_bar_1h" in REQUIRED_PRODUCTS
    assert "binance_usdm_trade_flow_1h" in DERIVED_PRODUCTS
    assert "binance_usdm_trade" not in REQUIRED_PRODUCTS
    assert INTERVAL_REQUIRED_FAMILIES["monthly/klines"] == "1h"
    assert "monthly/trades" in DISCOVERY_ARCHIVE_FAMILIES
    assert "monthly/trades" not in family_product_map()


def test_taker_flow_comes_from_kline_schema_not_trades() -> None:
    fields = KNOWN_ARCHIVE_SCHEMAS["klines"]["headerless"]
    assert kline_schema_supports_taker_flow(fields)
    assert set(KLINE_TAKER_FLOW_FIELDS).issubset(fields)
    assert "monthly/trades" not in OFFICIAL_ARCHIVE_FAMILIES.get("binance_usdm_trade_flow_1h", ())


def test_monthly_objects_are_canonical_and_daily_fill_gaps_only() -> None:
    monthly = ListingObject(
        key="data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip", size=10
    )
    overlapping_daily = ListingObject(
        key="data/futures/um/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01-15.zip", size=4
    )
    gap_daily = ListingObject(
        key="data/futures/um/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2020-02-01.zip", size=4
    )
    selected, collisions, rejections = select_nonoverlapping_objects(
        [monthly, overlapping_daily, gap_daily],
        checksum_keys={monthly.key, overlapping_daily.key, gap_daily.key},
    )
    assert [obj.key for obj in selected] == [monthly.key, gap_daily.key]
    assert collisions == ()
    assert rejections == ()


def test_duplicate_selected_month_is_an_economic_collision() -> None:
    # Both names must be real archive object names, or the case never reaches the
    # collision branch at all.
    first = ListingObject(
        key="data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip", size=10
    )
    second = ListingObject(
        key="data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.csv", size=11
    )
    assert object_period(first.key) == object_period(second.key) == "2020-01"
    selected, collisions, _rejections = select_nonoverlapping_objects(
        [first, second], checksum_keys={first.key, second.key}
    )
    assert collisions
    assert collisions[0]["kind"] == "economic_interval_collision"
    assert collisions[0]["interval"] == "2020-01"
    assert [obj.key for obj in selected] == [first.key]


def test_unchecksummed_monthly_is_rejected_with_explicit_daily_fallback() -> None:
    monthly = ListingObject(
        key="data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip", size=10
    )
    fallback = ListingObject(
        key="data/futures/um/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01-15.zip", size=4
    )
    selected, collisions, rejections = select_nonoverlapping_objects(
        [monthly, fallback], checksum_keys={fallback.key}
    )
    # An unproved monthly package is quarantined provenance, never a consumable canon.
    assert [obj.key for obj in selected] == [fallback.key]
    assert collisions == ()
    rejected = next(item for item in rejections if item["kind"] == MANIFEST_MONTHLY_REJECTED)
    assert rejected["key"] == monthly.key
    assert rejected["integrity_state"] == INTEGRITY_SIDECAR_ABSENT
    assert rejected["consumable"] is False
    covered = next(item for item in rejections if item["kind"] == MANIFEST_DAILY_FALLBACK)
    assert covered["key"] == fallback.key
    assert covered["replaces_month"] == "2020-01"


def test_quarantined_monthly_object_is_not_a_second_representation() -> None:
    monthly = ListingObject(
        key="data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip", size=10
    )
    selected, _collisions, rejections = select_nonoverlapping_objects(
        [monthly], checksum_keys={monthly.key}, quarantined={monthly.key}
    )
    assert selected == ()
    assert rejections[0]["integrity_state"] == INTEGRITY_QUARANTINED
    assert any(
        item["kind"] == MANIFEST_INTEGRITY_MISSING
        and item.get("status") == "no_daily_fallback_available"
        for item in rejections
    )
    assert object_integrity_state(monthly.key, checksum_keys={monthly.key}) == (
        INTEGRITY_SIDECAR_LISTED
    )
    # A listed sidecar is selection evidence; only a re-proved retained object is proof.
    assert object_integrity_state(
        monthly.key, checksum_keys={monthly.key}, proved_keys={monthly.key}
    ) == INTEGRITY_CHECKSUM_PROVED
    # Proof promotes validation state only inside the outcome-blind eligible domain: it can
    # never override an absent listed sidecar and re-admit the object to selection.
    assert object_integrity_state(
        monthly.key, checksum_keys=set(), proved_keys={monthly.key}
    ) == INTEGRITY_SIDECAR_ABSENT
    selected_after_proof, _found, _rejected = select_nonoverlapping_objects(
        [monthly], checksum_keys=set(), proved_keys={monthly.key}
    )
    assert selected_after_proof == ()


def test_daily_object_without_listed_authority_is_a_typed_gap() -> None:
    unproved = ListingObject(
        key="data/futures/um/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2020-03-02.zip", size=4
    )
    selected, _collisions, rejections = select_nonoverlapping_objects(
        [unproved], checksum_keys=set()
    )
    # Fallback carries the same precondition: unproved data never becomes usable.
    assert selected == ()
    gap = next(item for item in rejections if item["kind"] == MANIFEST_INTEGRITY_MISSING)
    assert gap["key"] == unproved.key
    assert gap["integrity_state"] == INTEGRITY_SIDECAR_ABSENT
    assert gap["consumable"] is False
    assert gap["blocking"] is True


def test_cost_sample_is_first_midpoint_last_daily_books(tmp_path: Path) -> None:
    dates = ("2020-01-01", "2020-01-10", "2020-01-20", "2020-01-31")
    payloads = {
        "bookTicker": _zip_bytes("b.csv", (FIXTURES / "headerless_book_ticker.csv").read_bytes()),
        "bookDepth": _zip_bytes("d.csv", (FIXTURES / "headerless_book_depth.csv").read_bytes()),
    }
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("daily/bookTicker", "bookTicker"), ("daily/bookDepth", "bookDepth")],
        payload_by_stem=payloads,
        months=dates,
    )
    inventory = build_family_inventory(index)
    direct = select_cost_calibration_sample(inventory=inventory, universe=["BTCUSDT"])
    assert direct["object_count"] == 6
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    sample = report.storage["cost_sample"]
    assert sample["selector"] == "first_midpoint_last_daily_book_v1"
    assert sample["object_count"] == 6
    keys = sample["keys"]
    assert any("2020-01-01" in key for key in keys)
    assert any("2020-01-31" in key for key in keys)
    assert object_calendar_date(keys[0]) is not None
    listed = _row("binance_usdm_cost_calibration", report).listed_object_count
    assert listed == 8
    assert sample["object_count"] < listed


def test_selected_storage_keeps_later_bounds_unknown(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    inventory = build_family_inventory(index)
    manifest = build_acquisition_manifest(inventory=inventory, universe=["BTCUSDT"])
    assert manifest["cadence_rule"] == "monthly_preferred_daily_gap_tail_v1"
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    selected = report.storage["selected_storage"]
    feasibility = report.storage["gate2_feasibility"]
    assert selected["selected_compressed_raw_bytes"] >= 0
    assert selected["largest_selected_compressed_object_bytes"] >= 0
    assert feasibility["normalized_catalog_bytes"] == "unknown"
    assert feasibility["temporary_high_water_bytes"] == "unknown"
    assert feasibility["operating_reserve_bytes"] == "unknown"
    assert feasibility["total_sufficiency"] == "unknown"
    # ADR-0017: an unknown total requirement can never be reported as sufficient.
    assert feasibility["gate2_storage_state"] == "unknown"
    assert feasibility["total_required_bytes"] is None
    assert set(feasibility["unknown_total_components"]) == {
        "normalized_catalog_bytes",
        "temporary_high_water_bytes",
        "operating_reserve_bytes",
    }
    assert "monthly/trades" in DISCOVERY_ARCHIVE_FAMILIES
    assert report.storage["physical_source_requirement"]["scope"] == (
        "selected_nonoverlapping_manifest_plus_cost_sample"
    )


def _write_lock(lock_path: Path, document: Mapping[str, Any]) -> str:
    lock_path.write_text(
        json.dumps(dict(document), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return file_sha256(lock_path)


def _seed_v2_authority(tmp_path: Path, index: MemoryObjectIndex) -> tuple[str, str]:
    """Execute once, then promote the durable lock to representative version-2 authority.

    The representative history preserves versions 0 and 1 exactly as review 98 requires:
    a pre-lock greedy plan document and the first locked plan with its content digest.
    """
    run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    lock_path = tmp_path / SAMPLE_PLAN_LOCK_FILENAME
    document = json.loads(lock_path.read_text())
    document["history"] = [
        {
            "plan_version": 0,
            "locked_at": "",
            "inputs": {"source": "pre_lock_greedy_plan"},
            "plan": {"entries": list(document["plan"]["entries"]), "blocked": []},
            "plan_digest": "",
        },
        {
            "plan_version": 1,
            "locked_at": document["locked_at"],
            "inputs": dict(document["inputs"]),
            "plan": dict(document["plan"]),
            "plan_digest": document["plan_digest"],
        },
    ]
    document["plan_version"] = 2
    return _write_lock(lock_path, document), file_sha256(tmp_path / BUDGET_LEDGER_FILENAME)


def test_candidate_plan_v3_is_not_a_lock_mutation(tmp_path: Path) -> None:
    # A selected acquisition family, so the durable plan really acquires and charges.
    index = _kline_manifest_index()
    lock_before, ledger_before = _seed_v2_authority(tmp_path, index)
    assert lock_before and ledger_before

    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT"),
        candidate_plan_only=True,
    )
    candidate = report.candidate_plan
    assert candidate["plan_version"] == 3
    assert candidate["state"] == "candidate_unmigrated"
    assert candidate["migration_authorized"] is False
    assert candidate["download_authorized"] is False
    assert candidate["prior_plan_version"] == 2
    assert candidate["prior_lock_sha256"] == lock_before
    assert candidate["digest_reuses_prior"] is False
    assert candidate["plan_digest"] not in set(candidate["prior_plan_digests"])
    assert candidate["plan"]["entries"]
    assert candidate["allowance"]["ledger_id"] == AMENDMENT_LEDGER_ID
    assert candidate["assertions"]["no_migration"] is True
    assert candidate["assertions"]["no_download"] is True

    # Prior authority is byte-identical, nothing was retrieved, and the executing plan
    # is still the durable version-2 plan.
    assert file_sha256(tmp_path / SAMPLE_PLAN_LOCK_FILENAME) == lock_before
    assert file_sha256(tmp_path / BUDGET_LEDGER_FILENAME) == ledger_before
    assert fetched == []
    assert report.samples == ()
    assert report.plan_lock["plan_version"] == 2
    # The comparable identity is the plan-content digest an exact version-3 lock would
    # record, not an envelope hash that could conceal plan-content reuse.
    assert candidate["plan_digest_domain"] == "plan_content_digest"
    assert candidate["plan_digest"] == plan_content_digest(
        SamplePlan.from_dict(candidate["plan"])
    )
    assert candidate["plan_digest"] != report.plan_lock["plan_digest"]
    assert candidate["candidate_envelope_digest"] != candidate["plan_digest"]
    # The candidate carries its own allowance identity, so its budget input differs even
    # though both ceilings happen to be the same number of bytes.
    assert candidate["inputs"]["budget_digest"] != report.plan_lock["inputs"]["budget_digest"]
    assert "relock" not in inspect.signature(run_source_qualification).parameters
    assert report.prospective_holdout["stream_collector_authorized"] is False
    assert report.budget["independent_object_cap_bytes"] is None


def test_candidate_requires_durable_prior_authority(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    # A fresh store has no version-2 lock, so no candidate may be fabricated from it.
    with pytest.raises(SourceQualificationError, match="requires the durable version-2"):
        run_source_qualification(
            store_root=tmp_path,
            index=index,
            current_contracts=_contracts("BTCUSDT"),
            candidate_plan_only=True,
        )
    _seed_v2_authority(tmp_path, index)
    (tmp_path / BUDGET_LEDGER_FILENAME).unlink()
    with pytest.raises(SourceQualificationError, match="requires the durable legacy budget"):
        run_source_qualification(
            store_root=tmp_path,
            index=index,
            current_contracts=_contracts("BTCUSDT"),
            candidate_plan_only=True,
        )


def test_candidate_allowance_is_separately_ledgered(tmp_path: Path) -> None:
    index = _kline_manifest_index()
    _lock_before, ledger_before = _seed_v2_authority(tmp_path, index)
    legacy = json.loads((tmp_path / BUDGET_LEDGER_FILENAME).read_text())
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT"),
        candidate_plan_only=True,
    )
    allowance = report.budget["architecture_amendment"]
    assert allowance["ledger_id"] == AMENDMENT_LEDGER_ID
    assert allowance["path"].endswith(AMENDMENT_LEDGER_FILENAME)
    assert allowance["allowance_bytes"] == GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES
    assert allowance["independent_object_cap_bytes"] is None
    assert allowance["charged"] is False
    # The legacy record is preserved untouched and is never charged again.
    assert allowance["legacy_ledger"]["sha256"] == ledger_before
    assert allowance["legacy_ledger"]["charged_again"] is False
    assert allowance["legacy_ledger"]["reconciled"] is False
    assert allowance["legacy_ledger"]["rewritten"] is False
    assert json.loads((tmp_path / BUDGET_LEDGER_FILENAME).read_text()) == legacy
    assert not (tmp_path / AMENDMENT_LEDGER_FILENAME).exists()
    assert report.budget["reconciliation"]["state"] == "not_reconciled_in_candidate_phase"
    # Compatible retained evidence stays reusable without erasing the legacy record.
    assert allowance["reusable_retained_object_count"] >= 1
    assert allowance["reusable_retained_bytes"] > 0


def test_architecture_plan_digest_does_not_reuse_a_prior_plan() -> None:
    key = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/BTCUSDT-1h-2020-01.zip"
    old = SamplePlan(
        entries=(
            SamplePlanEntry(
                family="monthly/trades",
                symbol="BTCUSDT",
                regime="early",
                products=("binance_usdm_trade",),
                key=f"{vision_prefix('monthly', 'trades')}BTCUSDT/BTCUSDT-trades-2020-01.zip",
                url=vision_object_url(
                    f"{vision_prefix('monthly', 'trades')}BTCUSDT/BTCUSDT-trades-2020-01.zip"
                ),
                byte_size=10,
                action="download",
            ),
        ),
        blocked=(),
        new_download_bytes=10,
        retained_bytes=0,
        budget_bytes=100,
        max_object_bytes=100,
        unique_new_objects=1,
        allowance_bytes=100,
    )
    new = SamplePlan(
        entries=(
            SamplePlanEntry(
                family="monthly/klines",
                symbol="BTCUSDT",
                regime="early",
                products=("binance_usdm_bar_1h",),
                key=key,
                url=vision_object_url(key),
                byte_size=10,
                action="download",
            ),
        ),
        blocked=(),
        new_download_bytes=10,
        retained_bytes=0,
        budget_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
        max_object_bytes=0,
        unique_new_objects=1,
        allowance_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
    )
    assert plan_content_digest(new) != plan_content_digest(old)


# --- review-99 inspectable manifest, taker-flow lineage, holdout, Gate 2 --------------


def _kline_manifest_index(months: Sequence[str] = CONTIGUOUS_MONTHS) -> MemoryObjectIndex:
    return _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1h"), ("daily/klines", "1h")],
        interval_map={"monthly/klines": ["1h"], "daily/klines": ["1h"]},
        payload_by_stem={
            "1h": _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
        },
        months=months,
    )


def test_manifest_rows_bind_identity_cadence_and_interval(tmp_path: Path) -> None:
    index = _kline_manifest_index()
    inventory = build_family_inventory(index)
    manifest = build_acquisition_manifest(inventory=inventory, universe=["BTCUSDT"])
    rows = manifest["rows"]
    assert rows
    for row in rows:
        assert set(row) == {
            "key",
            "family",
            "family_group",
            "symbol",
            "cadence",
            "byte_size",
            "integrity_state",
            "validation_state",
            "consumable",
            "sidecar_key",
            "sidecar_sha256",
            "economic_interval",
            "economic_interval_kind",
        }
        assert row["symbol"] == "BTCUSDT"
        assert row["family_group"] == "klines"
        # Selection is outcome-blind; nothing is consumable before its bytes are proved.
        assert row["integrity_state"] == INTEGRITY_SIDECAR_LISTED
        assert row["validation_state"] == VALIDATION_PENDING
        assert row["consumable"] is False
        assert row["sidecar_key"] == f"{row['key']}.CHECKSUM"
        assert row["byte_size"] > 0
    # Monthly packages are canonical, so each selected interval is a distinct month.
    assert {row["cadence"] for row in rows} == {"monthly"}
    assert sorted(row["economic_interval"] for row in rows) == list(CONTIGUOUS_MONTHS)
    assert {row["economic_interval_kind"] for row in rows} == {"month"}
    assert manifest["raw_validation_pending_keys"] == tuple(row["key"] for row in rows)
    assert manifest["consumable_object_count"] == 0

    # A re-proved retained object is the only thing that earns consumable authority.
    proved_key = rows[0]["key"]
    proved = build_acquisition_manifest(
        inventory=inventory,
        universe=["BTCUSDT"],
        proved_objects={proved_key: {"provider_checksum_sha256": "a" * 64}},
    )
    proved_row = next(row for row in proved["rows"] if row["key"] == proved_key)
    assert proved_row["integrity_state"] == INTEGRITY_CHECKSUM_PROVED
    assert proved_row["validation_state"] == VALIDATION_PROVED
    assert proved_row["consumable"] is True
    assert proved_row["sidecar_sha256"] == "a" * 64
    assert proved["consumable_object_count"] == 1

    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    published = report.acquisition_manifest["rows"]
    assert [row["key"] for row in published] == [row["key"] for row in rows]
    assert report.storage["acquisition_manifest"]["rows"] == published
    assert report.acquisition_manifest["integrity_rule"]


def test_manifest_uses_daily_fallback_for_an_unchecksummed_month(tmp_path: Path) -> None:
    index = _kline_manifest_index()
    monthly_prefix = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/"
    rejected = f"{monthly_prefix}BTCUSDT-1h-2020-02.zip"
    # Withdraw only that month's listed checksum; its bytes stay listed as provenance.
    index.objects[monthly_prefix] = [
        obj for obj in index.objects[monthly_prefix] if obj.key != f"{rejected}.CHECKSUM"
    ]
    inventory = build_family_inventory(index)
    manifest = build_acquisition_manifest(inventory=inventory, universe=["BTCUSDT"])
    keys = [row["key"] for row in manifest["rows"]]
    assert rejected not in keys
    assert any("/daily/" in key and "2020-02" in key for key in keys)
    rejection = next(
        item for item in manifest["rejections"] if item["kind"] == MANIFEST_MONTHLY_REJECTED
    )
    assert rejection["key"] == rejected
    assert rejection["integrity_state"] == INTEGRITY_SIDECAR_ABSENT
    assert any(
        item["kind"] == MANIFEST_DAILY_FALLBACK and item["replaces_month"] == "2020-02"
        for item in manifest["rejections"]
    )
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    assert rejected not in [row["key"] for row in report.acquisition_manifest["rows"]]
    assert report.acquisition_manifest["rejections"]


def test_overlapping_selected_coverage_fails_closed() -> None:
    month_row = {
        "key": "data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip",
        "family": "monthly/klines",
        "family_group": "klines",
        "symbol": "BTCUSDT",
        "cadence": "monthly",
        "byte_size": 10,
        "integrity_state": INTEGRITY_SIDECAR_LISTED,
        "economic_interval": "2020-01",
        "economic_interval_kind": "month",
    }
    day_row = {
        **month_row,
        "key": "data/futures/um/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01-05.zip",
        "family": "daily/klines",
        "cadence": "daily",
        "economic_interval": "2020-01-05",
        "economic_interval_kind": "date",
    }
    with pytest.raises(SourceQualificationError, match="covers a month by both cadences") as err:
        _assert_no_overlapping_coverage([month_row, day_row])
    assert err.value.context["kind"] == MANIFEST_OVERLAP
    with pytest.raises(SourceQualificationError, match="covers one economic interval twice"):
        _assert_no_overlapping_coverage([month_row, dict(month_row)])


def test_taker_flow_state_is_derived_from_the_kline_schema(tmp_path: Path) -> None:
    index = _kline_manifest_index()
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    bars = _row("binance_usdm_bar_1h", report)
    flow = _row("binance_usdm_trade_flow_1h", report)
    evidence = report.storage["taker_flow"]
    # Availability is established from the qualified 1h kline schema, never from trades.
    assert evidence["derived_from"] == "binance_usdm_bar_1h"
    assert evidence["supported"] is True
    assert evidence["requires_trades_or_aggtrades"] is False
    assert evidence["missing_fields"] == []
    assert set(KLINE_TAKER_FLOW_FIELDS).issubset(set(evidence["observed_schema_fields"]))
    assert evidence["evidence_key"]
    assert flow.coverage_state == bars.coverage_state
    assert flow.source_qualification_state == bars.source_qualification_state
    assert flow.release_blocked_derived == bars.release_blocked
    assert "monthly/trades" not in OFFICIAL_ARCHIVE_FAMILIES["binance_usdm_trade_flow_1h"]


def test_holdout_boundary_is_durable_and_replayed(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    first = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    boundary_path = tmp_path / HOLDOUT_BOUNDARY_FILENAME
    assert boundary_path.is_file()
    holdout = first.prospective_holdout
    assert holdout["boundary_state"] == "pinned_before_model_outcomes"
    assert holdout["outcome_blind"] is True
    assert holdout["stream_collector_authorized"] is False
    assert holdout["boundary_id"] == holdout_boundary_id(
        boundary_utc=holdout["boundary_utc"], replay_rule=holdout["replay_rule"]
    )
    assert holdout["retrieval_clock"] and holdout["source_availability_clock"]

    second = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    # A later run replays the pinned boundary; it never moves it.
    assert second.prospective_holdout["boundary_id"] == holdout["boundary_id"]
    assert second.prospective_holdout["boundary_utc"] == holdout["boundary_utc"]
    assert second.prospective_holdout["boundary_ms"] == holdout["boundary_ms"]

    document = json.loads(boundary_path.read_text())
    document["boundary_utc"] = "2030-01-01T00:00:00+00:00"
    boundary_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ResumeIntegrityError, match="does not match its own record"):
        HoldoutBoundary.load_or_pin(boundary_path, now_iso=holdout["boundary_utc"])


def test_cli_reports_unknown_gate2_state_and_candidate_mode() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "research"
        / "qualify_binance_usdm_harmonic_sources.py"
    )
    source = script.read_text(encoding="utf-8")
    tree = ast.parse(source)
    flags: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != "add_argument":
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    flags.append(arg.value)
    assert "--candidate-plan-only" in flags
    assert "--relock-sample-plan" not in flags
    # The summary must not print a Gate-2 verdict without its unknown components.
    assert "unknown_components=" in source
    assert "candidate_plan: state=" in source


def test_amendment_allowance_never_charges_the_legacy_ledger(tmp_path: Path) -> None:
    ledger = BudgetLedger(path=tmp_path / BUDGET_LEDGER_FILENAME, budget_bytes=1_000)
    ledger.reserve("data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip", 400)
    allowance = build_amendment_allowance(
        path=tmp_path / AMENDMENT_LEDGER_FILENAME,
        legacy_ledger=ledger,
        legacy_ledger_path=tmp_path / BUDGET_LEDGER_FILENAME,
        legacy_ledger_sha256="a" * 64,
        retained_keys={"k": 120},
        planned_new_bytes=1_000,
    )
    payload = allowance.to_dict()
    assert payload["allowance_bytes"] == GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES
    assert payload["remaining_bytes"] == GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES - 1_000
    assert payload["reusable_retained_bytes"] == 120
    assert payload["charged"] is False
    assert payload["legacy_ledger"]["charged_bytes"] == 400
    assert payload["legacy_ledger"]["charged_again"] is False
    assert ledger.charged_bytes == 400


def test_candidate_envelope_digest_never_replaces_the_plan_digest() -> None:
    key = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/BTCUSDT-1h-2020-01.zip"
    plan = SamplePlan(
        entries=(
            SamplePlanEntry(
                family="monthly/klines",
                symbol="BTCUSDT",
                regime="early",
                products=("binance_usdm_bar_1h",),
                key=key,
                url=vision_object_url(key),
                byte_size=10,
                action="download",
            ),
        ),
        blocked=(),
        new_download_bytes=10,
        retained_bytes=0,
        budget_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
        max_object_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
        unique_new_objects=1,
        allowance_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
    )
    envelope = candidate_envelope_digest(plan, allowance_id=AMENDMENT_LEDGER_ID)
    # The envelope binds allowance identity on top of the plan-content digest; it is a
    # different value, and the plan-content digest stays the comparable identity.
    assert envelope != plan_content_digest(plan)
    assert envelope != candidate_envelope_digest(plan, allowance_id="other")
    assert envelope == candidate_envelope_digest(plan, allowance_id=AMENDMENT_LEDGER_ID)
    assert plan_content_digest(plan) == plan_content_digest(
        SamplePlan.from_dict(plan.to_dict())
    )


# --- review-100 read-only prior authority, lineage, and exact version transition ------


def _metrics_index() -> MemoryObjectIndex:
    return _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/metrics", "metrics")],
        payload_by_stem={
            "metrics": _zip_bytes("m.csv", (FIXTURES / "headerless_metrics.csv").read_bytes())
        },
        months=CONTIGUOUS_MONTHS,
    )


def _outstanding_reservation(tmp_path: Path) -> tuple[str, str]:
    """Return an already-proved reservation to the legacy ledger, as a crash would leave."""
    ledger_path = tmp_path / BUDGET_LEDGER_FILENAME
    ledger = BudgetLedger.load(ledger_path, budget_bytes=GATE1_NEW_DOWNLOAD_BUDGET_BYTES)
    assert ledger is not None
    key, record = next(
        (name, item)
        for name, item in ledger.charges.items()
        if item["disposition"] == LEDGER_TRANSFERRED
    )
    ledger.charges.pop(key)
    ledger.reservations[key] = {"planned_bytes": int(record["planned_bytes"])}
    ledger.flush()
    return key, file_sha256(ledger_path)


def test_candidate_never_settles_a_proved_legacy_reservation(tmp_path: Path) -> None:
    index = _kline_manifest_index()
    lock_before, _ledger_before = _seed_v2_authority(tmp_path, index)
    reserved_key, ledger_before = _outstanding_reservation(tmp_path)

    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT"),
        candidate_plan_only=True,
    )
    # The reservation is provable, so a normal run would settle and rewrite the ledger.
    # A candidate phase must leave the exact crash-recovery bytes alone.
    assert file_sha256(tmp_path / BUDGET_LEDGER_FILENAME) == ledger_before
    assert file_sha256(tmp_path / SAMPLE_PLAN_LOCK_FILENAME) == lock_before
    assert not (tmp_path / AMENDMENT_LEDGER_FILENAME).exists()
    assert fetched == []
    assert report.samples == ()
    reloaded = BudgetLedger.load(
        tmp_path / BUDGET_LEDGER_FILENAME, budget_bytes=GATE1_NEW_DOWNLOAD_BUDGET_BYTES
    )
    assert reloaded is not None
    assert reserved_key in reloaded.reservations
    assert reserved_key not in reloaded.charges
    assert report.budget["reserved_object_count"] >= 1
    assert report.budget["reconciliation"]["state"] == "not_reconciled_in_candidate_phase"
    assert report.budget["architecture_amendment"]["legacy_ledger"]["sha256"] == ledger_before


def test_candidate_taker_flow_uses_reproved_retained_schema(tmp_path: Path) -> None:
    index = _kline_manifest_index()
    _seed_v2_authority(tmp_path, index)
    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT"),
        candidate_plan_only=True,
    )
    evidence = report.storage["taker_flow"]
    # No sample is acquired, yet the re-proved retained kline schema still qualifies the
    # derived product honestly.
    assert report.samples == ()
    assert fetched == []
    assert evidence["evidence_source"] == "reproved_retained_checkpoint"
    assert evidence["supported"] is True
    assert evidence["missing_fields"] == []
    assert evidence["evidence_key"]
    assert evidence["requires_trades_or_aggtrades"] is False
    flow = _row("binance_usdm_trade_flow_1h", report)
    assert flow.source_qualification_state != SOURCE_STATE_SAMPLE_PENDING
    # Nonblocking typed-gap coverage with no budget block: the inherited release block was
    # the same artificial current-invocation condition and is lifted with the state.
    assert evidence["release_blocked"] is False
    assert flow.release_blocked_derived is False


def test_candidate_taker_flow_is_honestly_pending_without_kline_evidence(
    tmp_path: Path,
) -> None:
    index = _metrics_index()
    _seed_v2_authority(tmp_path, index)
    report = run_source_qualification(
        store_root=tmp_path,
        index=index,
        current_contracts=_contracts("BTCUSDT"),
        candidate_plan_only=True,
    )
    evidence = report.storage["taker_flow"]
    assert evidence["supported"] is False
    assert evidence["evidence_key"] == ""
    assert evidence["observed_schema_fields"] == []
    flow = _row("binance_usdm_trade_flow_1h", report)
    assert flow.source_qualification_state == SOURCE_STATE_SAMPLE_PENDING
    assert flow.release_blocked_derived is True


def _load_lock_document(tmp_path: Path) -> dict[str, Any]:
    return json.loads((tmp_path / SAMPLE_PLAN_LOCK_FILENAME).read_text())


def _store_snapshot(root: Path) -> dict[str, str]:
    """Recursive byte-identity snapshot of an entire store, files and directories."""
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        snapshot[relative] = (
            "<dir>" if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest()
        )
    return snapshot


class _RecordingIndex:
    """Object index that records every listing or fetch it is asked to perform."""

    def __init__(self, index: MemoryObjectIndex) -> None:
        self._index = index
        self.calls: list[tuple[str, str]] = []

    def list_common_prefixes(self, prefix: str) -> list[str]:
        self.calls.append(("list_common_prefixes", prefix))
        return self._index.list_common_prefixes(prefix)

    def list_objects(self, prefix: str) -> list[ListingObject]:
        self.calls.append(("list_objects", prefix))
        return self._index.list_objects(prefix)

    def fetch_bytes(self, url: str) -> bytes:
        self.calls.append(("fetch_bytes", url))
        return self._index.fetch_bytes(url)


class _RecordingContracts:
    def __init__(self, source: MemoryCurrentContractSource) -> None:
        self._source = source
        self.calls = 0

    def fetch_exchange_info(self) -> ExchangeInfoResponse:
        self.calls += 1
        return self._source.fetch_exchange_info()


def _mutate_lock(document: dict[str, Any], mutation: str) -> dict[str, Any]:
    history = document["history"]
    if mutation == "version_one":
        document["plan_version"] = 1
    elif mutation == "version_three":
        document["plan_version"] = 3
    elif mutation == "missing_history":
        document["history"] = [history[1]]
    elif mutation == "duplicate_history":
        document["history"] = [history[0], dict(history[0])]
    elif mutation == "reversed_history":
        document["history"] = [history[1], history[0]]
    elif mutation == "missing_version_field":
        history[0].pop("plan_version")
    elif mutation == "string_version":
        history[0]["plan_version"] = "0"
    elif mutation == "boolean_version":
        history[1]["plan_version"] = True
    elif mutation == "malformed_v0_entries":
        history[0]["plan"] = {"entries": [{"key": "x"}], "blocked": []}
    elif mutation == "empty_v0_plan":
        history[0]["plan"] = {}
    else:
        history[1]["plan_digest"] = "d" * 64
    return document


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("version_one", "requires the durable version-2"),
        ("version_three", "requires the durable version-2"),
        ("missing_history", "exactly versions 0 and 1"),
        ("duplicate_history", "not the exact expected transition"),
        ("reversed_history", "not the exact expected transition"),
        ("missing_version_field", "has no version"),
        ("string_version", "is not an integer"),
        ("boolean_version", "is not an integer"),
        ("malformed_v0_entries", "missing identity fields"),
        ("empty_v0_plan", "no plan document"),
        ("wrong_history_digest", "digest does not match its plan"),
    ],
)
def test_invalid_transition_fails_before_any_candidate_mutation(
    tmp_path: Path, mutation: str, message: str
) -> None:
    index = _kline_manifest_index()
    _seed_v2_authority(tmp_path, index)
    _write_lock(
        tmp_path / SAMPLE_PLAN_LOCK_FILENAME, _mutate_lock(_load_lock_document(tmp_path), mutation)
    )

    before = _store_snapshot(tmp_path)
    recording = _RecordingIndex(index)
    contracts = _RecordingContracts(_contracts("BTCUSDT"))
    coinalyze = _coinalyze_anchor_transport()
    with pytest.raises(SourceQualificationError, match=message):
        run_source_qualification(
            store_root=tmp_path,
            index=recording,
            current_contracts=contracts,
            coinalyze_transport=coinalyze,
            coinalyze_api_key="sekret",
            candidate_plan_only=True,
        )
    # An invalid transition is rejected before a single directory, cache, checkpoint,
    # journal, holdout record, listing, contract fetch, or Coinalyze call happens.
    assert _store_snapshot(tmp_path) == before
    assert recording.calls == []
    assert contracts.calls == 0
    assert coinalyze.last_path == ""


def test_valid_candidate_preflight_returns_reusable_authority(tmp_path: Path) -> None:
    index = _kline_manifest_index()
    lock_before, ledger_before = _seed_v2_authority(tmp_path, index)
    authority = candidate_preflight(
        plan_lock_path=tmp_path / SAMPLE_PLAN_LOCK_FILENAME,
        budget_ledger_path=tmp_path / BUDGET_LEDGER_FILENAME,
        budget_bytes=GATE1_NEW_DOWNLOAD_BUDGET_BYTES,
    )
    assert authority.lock.plan_version == 2
    assert authority.lock_sha256 == lock_before
    assert authority.ledger_sha256 == ledger_before
    assert authority.prior_plan_digests
    # The preflight is read-only.
    assert file_sha256(tmp_path / SAMPLE_PLAN_LOCK_FILENAME) == lock_before
    assert file_sha256(tmp_path / BUDGET_LEDGER_FILENAME) == ledger_before


def test_candidate_reuse_detection_includes_the_derived_version_zero_identity(
    tmp_path: Path,
) -> None:
    index = _kline_manifest_index()
    _seed_v2_authority(tmp_path, index)
    lock = SamplePlanLock.load(tmp_path / SAMPLE_PLAN_LOCK_FILENAME)
    assert lock is not None

    key = f"{vision_prefix('monthly', 'klines')}BTCUSDT/1h/BTCUSDT-1h-2019-01.zip"
    legacy_plan = SamplePlan(
        entries=(
            SamplePlanEntry(
                family="monthly/klines",
                symbol="BTCUSDT",
                regime="early",
                products=("binance_usdm_bar_1h",),
                key=key,
                url=vision_object_url(key),
                byte_size=10,
                action="download",
            ),
        ),
        blocked=(),
        new_download_bytes=10,
        retained_bytes=0,
        budget_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
        max_object_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
        unique_new_objects=1,
        allowance_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
    )
    # The preserved version-0 record predates plan digests, so its identity must be
    # derived from the retained document rather than discarded.
    lock.history[0] = {
        "plan_version": 0,
        "locked_at": "",
        "inputs": {"source": "pre_lock_greedy_plan"},
        "plan": legacy_plan.to_dict(),
        "plan_digest": "",
    }
    digests = validate_prior_plan_history(lock)
    derived = plan_content_digest(legacy_plan)
    assert derived in digests

    ledger = BudgetLedger(path=tmp_path / BUDGET_LEDGER_FILENAME, budget_bytes=1_000)
    allowance = build_amendment_allowance(
        path=tmp_path / AMENDMENT_LEDGER_FILENAME,
        legacy_ledger=ledger,
        legacy_ledger_path=tmp_path / BUDGET_LEDGER_FILENAME,
        legacy_ledger_sha256="a" * 64,
        retained_keys={},
        planned_new_bytes=10,
    )
    inputs = PlanInputs(
        inventory_digest="a" * 64,
        listing_digest="b" * 64,
        membership_digest="c" * 64,
        code_config_digest="d" * 64,
        budget_digest="e" * 64,
        retained_digest="f" * 64,
    )
    # An identical historical plan cannot evade reuse detection behind the new allowance.
    with pytest.raises(ResumeIntegrityError, match="reuses a prior plan-content digest"):
        build_candidate_plan_v3(
            lock=lock,
            prior_lock_sha256="",
            plan=legacy_plan,
            inputs=inputs,
            allowance=allowance,
            prior_plan_digests=digests,
        )


def test_prior_history_validation_accepts_the_preserved_transition(tmp_path: Path) -> None:
    index = _kline_manifest_index()
    _seed_v2_authority(tmp_path, index)
    lock = SamplePlanLock.load(tmp_path / SAMPLE_PLAN_LOCK_FILENAME)
    assert lock is not None
    assert lock.plan_version == 2
    digests = validate_prior_plan_history(lock)
    assert [int(item["plan_version"]) for item in lock.history] == [0, 1]
    # Every preserved version contributes a comparable plan-content identity.
    assert lock.plan_digest in digests
    assert plan_content_digest(SamplePlan.from_dict(lock.history[0]["plan"])) in digests
    assert plan_content_digest(SamplePlan.from_dict(lock.history[1]["plan"])) in digests


# --- review-102 executable-level candidate preflight ----------------------------------

_CLI_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "research"
    / "qualify_binance_usdm_harmonic_sources.py"
)

# Everything the executable must not construct, load, or call before its preflight passes.
_CLI_FORBIDDEN_BEFORE_PREFLIGHT: tuple[str, ...] = (
    "HttpxTransport",
    "ListingCheckpointStore",
    "RetryJournal",
    "RetryRunner",
    "TransportObjectIndex",
    "FapiCurrentContractSource",
    "HttpxCoinalyzeTransport",
    "run_source_qualification",
    "write_qualification_report",
)


def _load_cli_module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _CLI_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_candidate_preflight_fails_before_any_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    index = _kline_manifest_index()
    _seed_v2_authority(tmp_path, index)
    _write_lock(
        tmp_path / SAMPLE_PLAN_LOCK_FILENAME,
        _mutate_lock(_load_lock_document(tmp_path), "version_three"),
    )
    report_path = tmp_path.parent / f"{tmp_path.name}_candidate_report.json"
    assert not report_path.exists()
    before = _store_snapshot(tmp_path)

    module = _load_cli_module("cex002_cli_preflight_under_test")
    used: list[str] = []

    def _forbid(name: str) -> Callable[..., Any]:
        def _raise(*_args: Any, **_kwargs: Any) -> Any:
            used.append(name)
            raise AssertionError(f"{name} ran before the candidate preflight")

        return _raise

    monkeypatch.setenv("COINALYZE_API_KEY", "cex002-secret-sentinel")
    for name in _CLI_FORBIDDEN_BEFORE_PREFLIGHT:
        assert hasattr(module, name)
        monkeypatch.setattr(module, name, _forbid(name))

    code = module.main(
        [
            "--store-root",
            str(tmp_path),
            "--report-path",
            str(report_path),
            "--candidate-plan-only",
        ]
    )
    captured = capsys.readouterr()
    # Exit 1 through the existing redacted CLI contract, with nothing created or used.
    assert code == 1
    assert used == []
    assert _store_snapshot(tmp_path) == before
    assert not report_path.exists()
    assert "ERROR: candidate plan construction requires the durable version-2 plan lock" in (
        captured.err
    )
    assert "listing checkpoint bootstrap" not in captured.err
    assert "cex002-secret-sentinel" not in captured.err
    assert "cex002-secret-sentinel" not in captured.out


def test_cli_noncandidate_initialization_is_unchanged() -> None:
    source = _CLI_SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    main = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    lines = {
        "preflight": None,
        "mkdir": None,
        "api_key": None,
        "transport": None,
        "checkpoint": None,
        "journal": None,
    }
    for node in ast.walk(main):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "candidate_preflight":
                lines["preflight"] = node.lineno
            elif isinstance(func, ast.Name) and func.id == "HttpxTransport":
                lines["transport"] = node.lineno
            elif isinstance(func, ast.Attribute) and func.attr == "mkdir":
                lines["mkdir"] = node.lineno
            elif isinstance(func, ast.Attribute) and func.attr == "get":
                if any(
                    isinstance(arg, ast.Constant) and arg.value == "COINALYZE_API_KEY"
                    for arg in node.args
                ):
                    lines["api_key"] = node.lineno
            elif isinstance(func, ast.Attribute) and func.attr == "load":
                owner = func.value
                if isinstance(owner, ast.Name) and owner.id == "ListingCheckpointStore":
                    lines["checkpoint"] = node.lineno
                elif isinstance(owner, ast.Name) and owner.id == "RetryJournal":
                    lines["journal"] = node.lineno
    assert all(value is not None for value in lines.values()), lines
    # The preflight strictly precedes every store, credential, transport, cache, and
    # journal operation, and the ordinary non-candidate path still performs them.
    for name in ("mkdir", "api_key", "transport", "checkpoint", "journal"):
        assert lines["preflight"] < lines[name], (name, lines)
