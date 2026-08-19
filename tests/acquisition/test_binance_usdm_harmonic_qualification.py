"""CEX-002 Gate 1 — prove the review-61 and review-64 defects are closed (no network)."""

from __future__ import annotations

import ast
import hashlib
import inspect
import io
import json
import zipfile
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    DERIVED_PRODUCTS,
    GATE1_MAX_NEW_OBJECT_BYTES,
    GATE1_NEW_DOWNLOAD_BUDGET_BYTES,
    MEMBERSHIP_FAMILY_PREFIXES,
    REQUIRED_PRODUCTS,
    SOURCE_PRODUCTS,
    VISION_S3_ENDPOINT,
    CoinalyzeClient,
    CoinalyzeResponse,
    ListingCheckpointStore,
    ListingObject,
    MemoryCoinalyzeTransport,
    MemoryCurrentContractSource,
    MemoryObjectIndex,
    ResumeIntegrityError,
    RetainedChecksumIndex,
    RetryJournal,
    RetryPolicy,
    RetryRunner,
    SampleCheckpointStore,
    SourceQualificationError,
    TransportObjectIndex,
    accept_qualification,
    identity_bytes,
    infer_schema_fields,
    is_retryable_failure,
    listing_request_identity,
    listing_request_key,
    parse_current_perpetuals,
    parse_provider_checksum,
    parse_s3_list_bucket,
    qualification_exit_code,
    refuse_restricted_scope,
    run_source_qualification,
    verify_provider_sidecar,
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
            targets: list[tuple[str, str]] = []
            if intervals:
                for interval in intervals:
                    interval_prefix = f"{symbol_prefix}{interval}/"
                    for month in ("2019-09", "2022-06", "2026-01"):
                        key = f"{interval_prefix}{symbol}-{stem}-{month}.zip"
                        targets.append((key, interval_prefix))
            else:
                for month in ("2019-09", "2022-06", "2026-01"):
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


def _coinalyze_transport() -> MemoryCoinalyzeTransport:
    return MemoryCoinalyzeTransport.from_files(
        {path: FIXTURES / name for path, name in COINALYZE_FIXTURE_FILES.items()}
    )


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
        native_symbols=["BTCUSDT"],
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
    report = run_source_qualification(store_root=tmp_path, index=index)
    trades = next(row for row in report.product_matrix if row.product == "binance_usdm_trade")
    assert trades.discovered_symbols == 2
    assert trades.official_complete is False
    assert trades.authority != "official"
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

    report = run_source_qualification(store_root=tmp_path, index=index)
    assert set(report.discovered_symbols) == {"BTCUSDT", "ETHUSDT"}
    bars = next(row for row in report.product_matrix if row.product == "binance_usdm_bar_1m")
    assert bars.official_complete is False
    assert bars.authority != "official"
    assert "ETHUSDT" in bars.uncovered_universe_symbols
    assert "ETHUSDT" not in bars.uncovered_listed_symbols
    assert "binance_usdm_bar_1m" in report.blocked_products
    gaps = [item for item in bars.universe_coverage_gaps if item["symbol"] == "ETHUSDT"]
    assert [item["status"] for item in gaps] == ["absent_family_prefix"]
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
    report = run_source_qualification(store_root=tmp_path, index=index)
    trades = next(row for row in report.product_matrix if row.product == "binance_usdm_trade")
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
            native_symbols=["ETHUSDT"],
            from_ts=1_577_836_800,
            to_ts=1_609_459_200,
        )


def test_coinalyze_rejects_symbol_absent_from_future_markets() -> None:
    transport = _coinalyze_transport()
    client = CoinalyzeClient(transport, api_key="sekret")
    with pytest.raises(SourceQualificationError, match="missing requested symbols"):
        client.qualify_binance_daily(
            native_symbols=["SOLUSDT"],
            from_ts=1_577_836_800,
            to_ts=1_609_459_200,
        )


def test_coinalyze_provenance_hashes_retained_raw_response_bytes() -> None:
    transport = _coinalyze_transport()
    client = CoinalyzeClient(transport, api_key="sekret")
    evidence = client.qualify_binance_daily(
        native_symbols=["BTCUSDT"],
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
            native_symbols=["BTCUSDT"],
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
        coinalyze_transport=_coinalyze_transport(),
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
    assert qualification_exit_code(report) in {0, 2}


def test_coinalyze_changes_liquidation_authority(tmp_path: Path) -> None:
    index = _index_with_family(
        symbols=["BTCUSDT"],
        families=[("monthly/trades", "trades")],
    )
    blocked = run_source_qualification(store_root=tmp_path / "a", index=index)
    liq_blocked = next(
        row for row in blocked.product_matrix if row.product == "binance_usdm_liquidation_observed"
    )
    assert liq_blocked.authority == "inaccessible"
    assert liq_blocked.official_complete is False
    qualified = run_source_qualification(
        store_root=tmp_path / "b",
        index=index,
        coinalyze_transport=_coinalyze_transport(),
        coinalyze_api_key="sekret",
    )
    liq = next(
        row for row in qualified.product_matrix if row.product == "binance_usdm_liquidation_observed"
    )
    assert liq.authority == "secondary"
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
    )
    report = run_source_qualification(store_root=tmp_path / "t", index=ticker_only)
    cost = next(row for row in report.product_matrix if row.product == "binance_usdm_cost_calibration")
    assert cost.official_complete is False
    both = _index_with_family(
        symbols=["BTCUSDT"],
        families=[
            ("monthly/bookTicker", "bookTicker"),
            ("monthly/bookDepth", "bookDepth"),
        ],
        payload_by_stem=book_payloads,
    )
    complete = run_source_qualification(store_root=tmp_path / "b", index=both)
    cost_both = next(
        row for row in complete.product_matrix if row.product == "binance_usdm_cost_calibration"
    )
    assert cost_both.listed_object_count == 6
    assert cost_both.official_complete is True


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
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"
    huge = []
    for month in ("2019-09", "2022-06", "2026-01"):
        key = f"{prefix}BTCUSDT-trades-{month}.zip"
        huge.append(ListingObject(key=key, size=600_000_000))
        index.bodies[vision_object_url(key)] = payload
    index.objects[prefix] = huge

    report = run_source_qualification(store_root=tmp_path, index=index)
    trade = next(row for row in report.product_matrix if row.product == "binance_usdm_trade")
    assert trade.sample_budget_blocked
    blocked = trade.sample_budget_blocked[0]
    assert blocked["kind"] == "sample_budget_exceeded"
    assert blocked["required_bytes"] == 600_000_000
    assert blocked["required_key"].startswith(prefix)
    # The source is reachable and fully inventoried; only the sample budget is unmet.
    assert trade.authority != "inaccessible"
    assert trade.listed_object_count == 3
    assert "sample_budget_exceeded" in trade.reason
    assert report.sample_plan["blocked"]
    assert any(
        item["kind"] == "sample_budget_exceeded" for item in report.incidents
    )


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
    run_source_qualification(store_root=tmp_path, index=index)
    second = run_source_qualification(store_root=tmp_path, index=index)
    plan = second.sample_plan
    assert plan["unique_retained_objects"] == 1
    assert plan["retained_bytes"] == only.size
    assert plan["new_download_bytes"] == 0


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
    """Abort a run whose synthetic objects all share one payload, after one object.

    Returns the index, the key proven before the abort, and the key whose provider
    sidecar was already retained when the abort fired but whose raw bytes were never
    fetched under its own key.
    """
    index = _index_with_family(symbols=["BTCUSDT"], families=[("monthly/trades", "trades")])
    real_fetch = index.fetch_bytes
    completed = {"n": 0}

    def _abort_after_one(url: str) -> bytes:
        if not url.endswith(".CHECKSUM"):
            if completed["n"] >= 1:
                raise _InjectedAbort(url)
            completed["n"] += 1
        return real_fetch(url)

    index.fetch_bytes = _abort_after_one  # type: ignore[method-assign]
    with pytest.raises(_InjectedAbort) as aborted:
        run_source_qualification(store_root=store_root, index=index)
    index.fetch_bytes = real_fetch  # type: ignore[method-assign]

    aborted_url = str(aborted.value.args[0])
    prefix = f"{vision_prefix('monthly', 'trades')}BTCUSDT/"
    pending_key = next(
        obj.key for obj in index.objects[prefix] if vision_object_url(obj.key) == aborted_url
    )
    document = json.loads((store_root / "cex002_qualification_progress.json").read_text())
    proven_key = next(iter(document["objects"]))
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

    # One broken leg withdraws provider authority: the object is retrieved over the
    # network, never silently adopted from another key's identical bytes.
    assert resumed.resume["recovered_samples"] == 0
    assert vision_object_url(pending_key) in fetched


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
