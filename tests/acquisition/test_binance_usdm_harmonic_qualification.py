"""CEX-002 Gate 1 — prove the review-61 and review-64 defects are closed (no network)."""

from __future__ import annotations

import ast
import hashlib
import inspect
import io
import json
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    BUDGET_LEDGER_FILENAME,
    CONTRACT_METADATA_FILENAME,
    CONTRACT_SNAPSHOT_DIRNAME,
    COINALYZE_ANCHOR_SYMBOLS,
    COVERAGE_BLOCKING_GAPS,
    COVERAGE_TYPED_GAPS,
    COVERAGE_UNRESOLVED_MEMBERSHIP,
    DERIVED_PRODUCTS,
    GATE1_MAX_NEW_OBJECT_BYTES,
    GATE1_NEW_DOWNLOAD_BUDGET_BYTES,
    LEDGER_NO_TRANSFER,
    LEDGER_TRANSFERRED,
    LEGACY_BUDGET_UNRESOLVED,
    LEGACY_PLAN_BACKUP_FILENAME,
    MEMBERSHIP_CONFIRMED,
    MEMBERSHIP_DATED_DELIVERY,
    MEMBERSHIP_DELIVERY,
    MEMBERSHIP_FAMILY_PREFIXES,
    MEMBERSHIP_SETTLEMENT_ARTIFACT,
    MEMBERSHIP_TRADIFI,
    MEMBERSHIP_UNRESOLVED,
    MEMBERSHIP_UNSUPPORTED_SEMANTICS,
    OFFICIAL_INCREMENTAL_ENDPOINTS,
    PLAN_INPUTS_CHANGED,
    REQUIRED_PRODUCTS,
    SAMPLE_PLAN_LOCK_FILENAME,
    SOURCE_PRODUCTS,
    SOURCE_STATE_MEMBERSHIP,
    SOURCE_STATE_OFFICIAL,
    SOURCE_STATE_SAMPLE_PENDING,
    SOURCE_STATE_SECONDARY,
    SEMANTICS_INCOHERENT_IDENTITY,
    SEMANTICS_SUPPORTED,
    SEMANTICS_UNKNOWN_STATUS,
    SEMANTICS_UNKNOWN_UNDERLYING,
    SOURCE_STATE_TYPED_GAPS,
    VISION_S3_ENDPOINT,
    BudgetLedger,
    CoinalyzeClient,
    CoinalyzeResponse,
    ExchangeInfoResponse,
    ListingCheckpointStore,
    ListingObject,
    MemoryCoinalyzeTransport,
    MemoryCurrentContractSource,
    MemoryObjectIndex,
    OfficialContractMetadataStore,
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
    accept_qualification,
    build_family_inventory,
    build_sample_plan,
    canonical_contract_row,
    classify_membership,
    contract_close_ms,
    contract_provenance,
    contract_semantics_state,
    exchange_info_server_time_ms,
    family_product_map,
    identity_bytes,
    infer_schema_fields,
    is_confirmed_perpetual_row,
    is_retryable_failure,
    listing_request_identity,
    listing_request_key,
    listing_authority_digest,
    listing_authority_manifest,
    membership_evidence_digest,
    object_period,
    parse_current_perpetuals,
    plan_content_digest,
    parse_exchange_info_rows,
    parse_provider_checksum,
    parse_s3_list_bucket,
    qualification_exit_code,
    refuse_restricted_scope,
    run_source_qualification,
    retained_evidence_digest,
    retained_evidence_snapshot,
    validate_exchange_info_response,
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


def _distinct_object_payload(key: str) -> bytes:
    """Valid headerless trades archive bytes unique to one remote object key.

    Real remote objects never share bytes. Deriving the trade rows from the object key
    gives every synthetic object its own content address, so an object that was never
    downloaded is genuinely absent from the content-addressed store.
    """
    seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)
    rows = []
    for offset in range(2):
        price = float(7000 + seed % 5000 + offset)
        qty = 0.5 + offset / 4
        rows.append(
            f"{seed + offset},{price},{qty},{round(price * qty, 4)},"
            f"{1577836800000 + seed % 1000000 + offset},"
            f"{'true' if offset % 2 == 0 else 'false'}"
        )
    return _stable_zip_bytes("trades.csv", ("\n".join(rows) + "\n").encode("utf-8"))


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
            for key, object_prefix in targets:
                if payload_for_key is not None:
                    payload = payload_for_key(key)
                else:
                    payload = payloads.get(stem, default_payload)
                listing = ListingObject(key=key, size=len(payload))
                objects.setdefault(object_prefix, []).append(listing)
                url = vision_object_url(key)
                bodies[url] = payload
                bodies[vision_object_url(f"{key}.CHECKSUM")] = _checksum_text(
                    payload, key.rsplit("/", 1)[-1]
                )
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
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/trades", "trades")],
    )
    first = run_source_qualification(store_root=tmp_path, index=index)
    assert first.samples
    sample = first.samples[0]
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


def test_bar_1m_counts_only_one_minute_interval(tmp_path: Path) -> None:
    kline_zip = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1m"), ("monthly/trades", "trades")],
        interval_map={"monthly/klines": ["1m", "5m"]},
        payload_by_stem={"1m": kline_zip, "trades": _zip_bytes("t.csv", (FIXTURES / "headerless_trades.csv").read_bytes())},
    )
    report = run_source_qualification(store_root=tmp_path, index=index)
    bars = next(row for row in report.product_matrix if row.product == "binance_usdm_bar_1m")
    assert bars.listed_object_count == 3
    assert all("/5m/" not in sample.key for sample in report.samples if sample.product == "binance_usdm_bar_1m")
    assert any("/1m/" in sample.key for sample in report.samples if sample.product == "binance_usdm_bar_1m")


def test_empty_listed_symbol_prefix_blocks_official_complete(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/trades", "trades"), ("monthly/aggTrades", "aggTrades")],
    )
    trade_prefix = vision_prefix("monthly", "trades")
    agg_prefix = vision_prefix("monthly", "aggTrades")
    index.prefixes[trade_prefix] = sorted(
        [*index.prefixes[trade_prefix], f"{trade_prefix}ETHUSDT/"]
    )
    index.prefixes[agg_prefix] = sorted(
        [*index.prefixes[agg_prefix], f"{agg_prefix}ETHUSDT/"]
    )
    index.objects[f"{trade_prefix}ETHUSDT/"] = []
    index.objects[f"{agg_prefix}ETHUSDT/"] = []
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT", "ETHUSDT")
    )
    trades = _row("binance_usdm_trade", report)
    assert trades.discovered_symbols == 2
    assert trades.official_complete is False
    assert trades.release_blocked is True
    # A listed prefix with no objects is a coverage fact, not a loss of source authority.
    assert trades.coverage_state == COVERAGE_BLOCKING_GAPS
    assert "ETHUSDT" in trades.uncovered_listed_symbols
    assert "binance_usdm_trade" in report.blocked_products
    coverage = report.storage["symbol_coverage"]["binance_usdm_trade"]
    assert coverage["monthly/trades/ETHUSDT"] == 0
    assert coverage["monthly/aggTrades/ETHUSDT"] == 0


def test_absent_family_prefix_blocks_official_complete(tmp_path: Path) -> None:
    # ETHUSDT is in the discovered archive union but has no 1m kline prefix at all.
    index = _index_with_family(
        symbols=["BTCUSDT", "ETHUSDT"],
        families=[("monthly/trades", "trades")],
    )
    kline_prefix = vision_prefix("monthly", "klines")
    kline_zip = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index.prefixes[kline_prefix] = [f"{kline_prefix}BTCUSDT/"]
    symbol_prefix = f"{kline_prefix}BTCUSDT/"
    interval_prefix = f"{symbol_prefix}1m/"
    index.prefixes[symbol_prefix] = [interval_prefix]
    index.objects[interval_prefix] = []
    for month in ("2019-09", "2022-06", "2026-01"):
        key = f"{interval_prefix}BTCUSDT-1m-{month}.zip"
        index.objects[interval_prefix].append(ListingObject(key=key, size=len(kline_zip)))
        index.bodies[vision_object_url(key)] = kline_zip
        index.bodies[vision_object_url(f"{key}.CHECKSUM")] = _checksum_text(
            kline_zip, key.rsplit("/", 1)[-1]
        )

    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT", "ETHUSDT")
    )
    assert set(report.discovered_symbols) == {"BTCUSDT", "ETHUSDT"}
    bars = _row("binance_usdm_bar_1m", report)
    assert bars.official_complete is False
    assert bars.release_blocked is True
    assert bars.coverage_state == COVERAGE_BLOCKING_GAPS
    assert "ETHUSDT" in bars.uncovered_universe_symbols
    assert "ETHUSDT" not in bars.uncovered_listed_symbols
    assert "binance_usdm_bar_1m" in report.blocked_products
    gaps = [item for item in bars.universe_coverage_gaps if item["symbol"] == "ETHUSDT"]
    assert [item["status"] for item in gaps] == ["current_unarchived"]
    assert gaps[0]["blocking"] is True
    assert gaps[0]["family_group"] == "klines"
    coverage = report.storage["symbol_coverage"]["binance_usdm_bar_1m"]
    assert coverage["monthly/klines/ETHUSDT"] == 0
    assert coverage["monthly/klines/BTCUSDT"] == 3
    assert report.storage["universe_coverage_gaps"]["binance_usdm_bar_1m"]


def test_universe_coverage_gap_is_reported_in_the_blocking_reason(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["BTCUSDT", "ETHUSDT"],
        families=[("monthly/trades", "trades")],
    )
    agg_prefix = vision_prefix("monthly", "aggTrades")
    index.prefixes[agg_prefix] = [f"{agg_prefix}BTCUSDT/"]
    index.objects[f"{agg_prefix}BTCUSDT/"] = []
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT", "ETHUSDT")
    )
    trades = _row("binance_usdm_trade", report)
    assert trades.official_complete is False
    assert "ETHUSDT" in trades.uncovered_universe_symbols
    assert "discovered universe symbols lack required family coverage" in trades.reason


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
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/trades", "trades")],
    )
    checksum_urls = [url for url in index.bodies if url.endswith(".CHECKSUM")]
    for url in checksum_urls:
        del index.bodies[url]
    report = run_source_qualification(store_root=tmp_path, index=index)
    trades = next(row for row in report.product_matrix if row.product == "binance_usdm_trade")
    assert trades.official_complete is False
    assert trades.authority != "official"
    assert "binance_usdm_trade" in report.blocked_products


def test_licensed_quotes_argument_removed() -> None:
    signature = inspect.signature(run_source_qualification)
    assert "licensed_quotes" not in signature.parameters


def test_derived_products_do_not_block_source_gate(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[
            ("monthly/trades", "trades"),
            ("monthly/klines", "1m"),
            ("monthly/metrics", "metrics"),
            ("monthly/fundingRate", "fundingRate"),
            ("monthly/premiumIndexKlines", "premiumIndexKlines"),
            ("monthly/markPriceKlines", "markPriceKlines"),
            ("monthly/indexPriceKlines", "indexPriceKlines"),
            ("monthly/bookTicker", "bookTicker"),
            ("monthly/bookDepth", "bookDepth"),
        ],
        interval_map={
            "monthly/klines": ["1m"],
            "monthly/premiumIndexKlines": ["1m"],
            "monthly/markPriceKlines": ["1m"],
            "monthly/indexPriceKlines": ["1m"],
        },
        payload_by_stem={
            "1m": _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes()),
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
    assert authorities["binance_usdm_trade_flow"] == "unsupported"
    assert authorities["binance_usdm_liquidation_observed"] == "secondary"
    assert "binance_usdm_liquidation_observed" not in report.blocked_products
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
    liq_blocked = _row("binance_usdm_liquidation_observed", blocked)
    assert liq_blocked.authority == "inaccessible"
    assert liq_blocked.official_complete is False
    qualified = run_source_qualification(
        store_root=tmp_path / "b",
        index=index,
        current_contracts=_contracts("BTCUSDT", "ETHUSDT"),
        coinalyze_transport=_coinalyze_anchor_transport(),
        coinalyze_api_key="sekret",
    )
    liq = _row("binance_usdm_liquidation_observed", qualified)
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
    ticker_only = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/bookTicker", "bookTicker")],
        payload_by_stem=book_payloads,
        months=CONTIGUOUS_MONTHS,
    )
    report = run_source_qualification(
        store_root=tmp_path / "t", index=ticker_only, current_contracts=_contracts("BTCUSDT")
    )
    cost = _row("binance_usdm_cost_calibration", report)
    assert cost.official_complete is False
    both = _index_with_family(
        symbols=["BTCUSDT"],
        families=[
            ("monthly/bookTicker", "bookTicker"),
            ("monthly/bookDepth", "bookDepth"),
        ],
        payload_by_stem=book_payloads,
        months=CONTIGUOUS_MONTHS,
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
    index = _index_with_family(
        symbols=["BTCUSDT", "ETHUSDT"],
        families=[("monthly/trades", "trades")],
    )
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
    assert "binance_usdm_trade_flow" in DERIVED_PRODUCTS
    assert "binance_usdm_liquidation_observed" in SOURCE_PRODUCTS
    assert list(REQUIRED_PRODUCTS)[:3] == [
        "binance_usdm_perpetual_membership",
        "binance_usdm_trade",
        "binance_usdm_bar_1m",
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
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
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
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
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
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
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
    index = _index_with_family(symbols=["BTCUSDT", "ETHUSDT"], families=[("monthly/trades", "trades")])
    clean = run_source_qualification(store_root=tmp_path / "clean", index=index)
    resumed_root = tmp_path / "resumed"
    first = run_source_qualification(store_root=resumed_root, index=index)
    second = run_source_qualification(store_root=resumed_root, index=index)
    assert second.resume["reused_samples"] > 0
    assert identity_bytes(first) == identity_bytes(second)
    # Execution-plane differences must not change the semantic identity of the result.
    assert identity_bytes(clean) == identity_bytes(second)


def test_sample_plan_is_persisted_before_download_and_prefers_smallest(tmp_path: Path) -> None:
    small = _zip_bytes("t.csv", (FIXTURES / "headerless_trades.csv").read_bytes())
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"
    objs = list(index.objects[prefix])
    # Make the middle-regime bucket offer a large and a small candidate.
    big_key = f"{prefix}BTCUSDT-trades-2022-07.zip"
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
    payload = _zip_bytes("t.csv", (FIXTURES / "headerless_trades.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/trades", "trades"), ("monthly/aggTrades", "aggTrades")],
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
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"

    fetched: list[str] = []
    real_fetch = index.fetch_bytes

    def _tracking(url: str) -> bytes:
        fetched.append(url)
        return real_fetch(url)

    index.fetch_bytes = _tracking  # type: ignore[method-assign]

    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    trade = next(row for row in report.product_matrix if row.product == "binance_usdm_trade")
    assert trade.sample_budget_blocked
    blocked = trade.sample_budget_blocked[0]
    assert blocked["kind"] == "sample_budget_exceeded"
    assert blocked["required_bytes"] == 600_000_000
    assert blocked["required_key"].startswith(prefix) or blocked["required_key"].startswith(
        f"{vision_prefix('monthly', 'aggTrades')}BTCUSDT/"
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
    payload = _zip_bytes("t.csv", (FIXTURES / "headerless_trades.csv").read_bytes())
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"
    index.objects[prefix] = [
        ListingObject(key=f"{prefix}BTCUSDT-trades-{month}.zip", size=600_000_000)
        for month in ("2019-09", "2022-06", "2026-01")
    ]
    for obj in index.objects[prefix]:
        index.bodies[vision_object_url(obj.key)] = payload
    report = run_source_qualification(store_root=tmp_path, index=index)
    trade = next(row for row in report.product_matrix if row.product == "binance_usdm_trade")
    # Full listed byte inventory is preserved, never truncated to the execution budget.
    assert trade.listed_bytes == 1_800_000_000
    assert report.storage["byte_count_exact"]["binance_usdm_trade"] == 1_800_000_000


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
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
    run_source_qualification(store_root=tmp_path, index=index)
    progress = tmp_path / "cex002_qualification_progress.json"
    progress.write_text("{corrupted")
    with pytest.raises(ResumeIntegrityError):
        run_source_qualification(store_root=tmp_path, index=index)


def test_substituted_provider_checksum_in_checkpoint_fails_closed(tmp_path: Path) -> None:
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
    run_source_qualification(store_root=tmp_path, index=index)
    progress = tmp_path / "cex002_qualification_progress.json"
    document = json.loads(progress.read_text())
    key = next(iter(document["objects"]))
    document["objects"][key]["provider_checksum"] = "b" * 64
    progress.write_text(json.dumps(document))
    with pytest.raises(ResumeIntegrityError, match="provider checksum disagrees"):
        run_source_qualification(store_root=tmp_path, index=index)


def test_sample_checkpoint_url_must_match_the_object_key(tmp_path: Path) -> None:
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
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
    payload = _zip_bytes("t.csv", (FIXTURES / "headerless_trades.csv").read_bytes())
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"
    only_key = f"{prefix}BTCUSDT-trades-2020-01.zip"
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
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"
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
        families=[("monthly/trades", "trades")],
        payload_for_key=_distinct_object_payload,
    )


def test_abort_after_completed_sample_resumes_missing_objects_only(tmp_path: Path) -> None:
    clean_index = _distinct_bytes_index()
    clean = run_source_qualification(store_root=tmp_path / "clean", index=clean_index)

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
        run_source_qualification(store_root=store_root, index=aborting)

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

    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
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
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"
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
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
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
    return _index_with_family(
        symbols=symbols,
        families=[("monthly/trades", "trades")],
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
        products=("binance_usdm_trade",),
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


def test_no_public_switch_can_reselect_the_locked_plan() -> None:
    assert "relock_sample_plan" not in inspect.signature(run_source_qualification).parameters
    script = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "research"
        / "qualify_binance_usdm_harmonic_sources.py"
    )
    source = script.read_text(encoding="utf-8")
    # A new plan version requires a fresh reviewer authorization, not a CLI flag.
    assert "--relock-sample-plan" not in source
    assert "relock" not in source


def test_new_download_budget_is_cumulative_across_invocations(tmp_path: Path) -> None:
    index = _trades_index(["BTCUSDT"])
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"
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
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/trades", "trades"), ("monthly/aggTrades", "aggTrades")],
        payload_by_stem={
            "aggTrades": _zip_bytes("a.csv", b"1,7000.0,0.5,10,12,1577836800000,true\n")
        },
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
    # monthly/trades serves both the membership and trade products; it is counted once.
    assert requirement["object_count"] == 6
    assert requirement["compressed_raw_bytes"] == 600_000_000_000_000
    assert requirement["universe_basis"] == "confirmed_perpetual_membership"
    feasibility = report.storage["gate2_feasibility"]
    assert feasibility["gate2_storage_state"] == "insufficient"
    assert feasibility["shortfall_bytes"] > 0
    assert feasibility["local_available_bytes"] is not None
    assert feasibility["normalized_catalog_bytes"]["treated_as_zero"] is False
    assert feasibility["normalized_catalog_bytes"]["state"] == "unknown"
    assert any(item["kind"] == "gate2_storage_insufficient" for item in report.incidents)
    assert report.storage["logical_product_totals_overlap"] is True
    # Storage insufficiency blocks Gate 2; it never relabels a reachable source.
    trades = _row("binance_usdm_trade", report)
    assert trades.authority != "inaccessible"
    assert trades.source_qualification_state == SOURCE_STATE_SAMPLE_PENDING


# --- review-75 source qualification versus temporal coverage --------------------------


def test_object_period_reads_monthly_and_daily_object_keys() -> None:
    assert object_period("x/BTCUSDT-trades-2020-01.zip") == "2020-01"
    assert object_period("x/BTCUSDT-trades-2020-01-05.zip") == "2020-01"
    assert object_period("x/BTCUSDT-trades.zip") is None


def test_family_launch_gap_keeps_official_authority(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/trades", "trades"), ("monthly/aggTrades", "aggTrades")],
        payload_by_stem={
            "aggTrades": _zip_bytes("a.csv", b"1,7000.0,0.5,10,12,1577836800000,true\n")
        },
        months=CONTIGUOUS_MONTHS,
        months_by_family={"monthly/aggTrades": CONTIGUOUS_MONTHS[1:]},
    )
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    trades = _row("binance_usdm_trade", report)
    # aggTrades simply launched later; the official source keeps its authority.
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
    temporal = report.storage["symbol_temporal_coverage"]["binance_usdm_trade"]["BTCUSDT"]
    assert temporal == {"first": "2020-01", "last": "2020-03", "months": 3}


def test_interior_month_gap_blocks_release_without_withdrawing_authority(
    tmp_path: Path,
) -> None:
    kline_zip = _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/klines", "1m")],
        interval_map={"monthly/klines": ["1m"]},
        payload_by_stem={"1m": kline_zip},
        months=("2020-01", "2020-03"),
    )
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT")
    )
    bars = _row("binance_usdm_bar_1m", report)
    # A missing interior month is a real, blocking coverage gap, not a source failure.
    assert bars.authority == "official"
    assert bars.source_qualification_state == SOURCE_STATE_OFFICIAL
    assert bars.coverage_state == COVERAGE_BLOCKING_GAPS
    assert "interior_month_gap" in bars.coverage_gap_kinds
    assert bars.release_blocked is True
    assert "binance_usdm_bar_1m" in report.blocked_products
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
    liquidation = _row("binance_usdm_liquidation_observed", report)
    assert liquidation.authority == "secondary"
    assert liquidation.source_qualification_state == SOURCE_STATE_SECONDARY
    assert liquidation.coverage_state == COVERAGE_BLOCKING_GAPS
    assert liquidation.official_complete is False
    assert liquidation.release_blocked is True
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
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"
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
    assert full["binance_usdm_trade"] == 6
    assert confirmed["binance_usdm_trade"] == 3
    row = _row("binance_usdm_trade", report)
    assert row.listed_object_count == 6
    assert row.accepted_universe_object_count == 3
    assert report.storage["confirmed_universe_totals"]["scope"] == report.membership[
        "universe_basis"
    ]


# --- review-76 evidence-based temporal windows ----------------------------------------


def _kline_index(months: Sequence[str] = CONTIGUOUS_MONTHS, **kwargs: Any) -> MemoryObjectIndex:
    return _index_with_family(
        symbols=["AAAUSDT", "BBBUSDT"],
        families=[("monthly/klines", "1m")],
        interval_map={"monthly/klines": ["1m"]},
        payload_by_stem={
            "1m": _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes())
        },
        months=months,
        **kwargs,
    )


def _drop_object(index: MemoryObjectIndex, symbol: str, month: str) -> None:
    prefix = f"{vision_prefix('monthly', 'klines')}{symbol}/1m/"
    key = f"{prefix}{symbol}-1m-{month}.zip"
    index.objects[prefix] = [obj for obj in index.objects[prefix] if obj.key != key]
    index.bodies.pop(vision_object_url(key), None)
    index.bodies.pop(vision_object_url(f"{key}.CHECKSUM"), None)


def test_unexplained_head_gap_blocks_release(tmp_path: Path) -> None:
    index = _kline_index()
    _drop_object(index, "BBBUSDT", "2020-01")
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("AAAUSDT", "BBBUSDT")
    )
    bars = _row("binance_usdm_bar_1m", report)
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
    bars = _row("binance_usdm_bar_1m", report)
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
    bars = _row("binance_usdm_bar_1m", report)
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
    bars = _row("binance_usdm_bar_1m", report)
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
        families=[("monthly/klines", "1m"), ("monthly/fundingRate", "fundingRate")],
        interval_map={"monthly/klines": ["1m"]},
        payload_by_stem={
            "1m": _zip_bytes("k.csv", (FIXTURES / "headerless_klines.csv").read_bytes()),
            "fundingRate": _zip_bytes("f.csv", (FIXTURES / "headed_funding.csv").read_bytes()),
        },
        months=CONTIGUOUS_MONTHS,
    )
    _drop_object(index, "AAAUSDT", "2020-03")
    # AAAUSDT is proven perpetual by realized funding but has no lifecycle evidence.
    report = run_source_qualification(
        store_root=tmp_path, index=index, current_contracts=_contracts("BBBUSDT")
    )
    bars = _row("binance_usdm_bar_1m", report)
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
    liquidation = _row("binance_usdm_liquidation_observed", report)
    # Every unmapped confirmed perpetual is retained as product gap evidence.
    assert len(liquidation.universe_coverage_gaps) == 210
    assert len(liquidation.uncovered_universe_symbols) == 210
    assert liquidation.release_blocked is True


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
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"
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
