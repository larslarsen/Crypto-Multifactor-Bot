"""CEX-002 Gate 1 — prove the review-61 and review-64 defects are closed (no network)."""

from __future__ import annotations

import ast
import hashlib
import inspect
import io
import json
import zipfile
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    DERIVED_PRODUCTS,
    REQUIRED_PRODUCTS,
    SOURCE_PRODUCTS,
    CoinalyzeClient,
    CoinalyzeResponse,
    ListingObject,
    MemoryCoinalyzeTransport,
    MemoryCurrentContractSource,
    MemoryObjectIndex,
    SourceQualificationError,
    TransportObjectIndex,
    accept_qualification,
    identity_bytes,
    infer_schema_fields,
    parse_current_perpetuals,
    parse_provider_checksum,
    parse_s3_list_bucket,
    qualification_exit_code,
    refuse_restricted_scope,
    run_source_qualification,
    vision_object_url,
    vision_prefix,
    write_s3_list_bucket,
)
from source_audit.download import StreamResponse, TimeoutConfig

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "binance_usdm_harmonic_qualification"


def _zip_bytes(name: str, payload: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as handle:
        handle.writestr(name, payload)
    return buf.getvalue()


def _checksum_text(payload: bytes, filename: str) -> bytes:
    return f"{hashlib.sha256(payload).hexdigest()}  {filename}\n".encode()


def _load_json(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _index_with_family(
    *,
    symbols: list[str],
    families: list[tuple[str, str]],
    interval_map: dict[str, list[str]] | None = None,
    payload_by_stem: dict[str, bytes] | None = None,
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
