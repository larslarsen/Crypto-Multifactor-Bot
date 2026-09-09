from __future__ import annotations

import hashlib
import json
import sqlite3
import weakref
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import cryptofactors.ingest.binance_usdm_liquidation_observed as subject
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    PRODUCT_BAR_1H,
    PRODUCT_FUNDING_REALIZED,
    PRODUCT_OPEN_INTEREST_5M,
    final_product_schema,
    native_identity,
    product_schema_identity,
)


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _write(path: Path, body: bytes) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return hashlib.sha256(body).hexdigest(), len(body)


def _raw(
    tmp_path: Path,
    *,
    native: str = "BTCUSDT",
    base: str = "BTC",
    quote: str = "USDT",
    start: int = 1_609_286_400,
    end: int = 1_609_459_200,
    points: str | None = None,
) -> subject.RawLiquidationObject:
    provider = subject.coinalyze_perp_symbol(native)
    if points is None:
        points = '[{"t":1609286400,"l":1.000000000000000001,"s":0},{"t":1609459200,"l":0,"s":2.5}]'
    body = (
        '[{"symbol":'
        + json.dumps(provider, ensure_ascii=False)
        + ',"history":'
        + points
        + "}]"
    ).encode()
    digest, size = _write(tmp_path / f"raw-{hashlib.sha256(native.encode()).hexdigest()}.json", body)
    params = {"symbols": provider, "interval": "daily", "from": str(start), "to": str(end), "convert_to_usd": "false"}
    return subject.RawLiquidationObject(
        identity=f"/liquidation-history?{subject.urlencode(params)}",
        native_symbol=native,
        provider_symbol=provider,
        base_asset=base,
        quote_asset=quote,
        path=tmp_path / f"raw-{hashlib.sha256(native.encode()).hexdigest()}.json",
        source_sha256=digest,
        byte_size=size,
        retrieved_at="2026-08-30T00:00:00+00:00",
        request_from_s=start,
        request_to_s=end,
        point_count=points.count('"t"'),
    )


def _mapping(raw: subject.RawLiquidationObject) -> dict[str, subject.LiquidationMapping]:
    return {raw.native_symbol: subject.LiquidationMapping(raw.native_symbol, raw.provider_symbol, raw.base_asset, raw.quote_asset)}


def _generic_row(schema: pa.Schema) -> dict[str, object]:
    row: dict[str, object] = {}
    for field in schema:
        if field.nullable:
            row[field.name] = None
        elif pa.types.is_dictionary(field.type) or pa.types.is_string(field.type):
            row[field.name] = "x"
        elif pa.types.is_decimal(field.type):
            row[field.name] = Decimal("0")
        elif pa.types.is_boolean(field.type):
            row[field.name] = False
        elif pa.types.is_integer(field.type):
            row[field.name] = 0
        else:
            raise AssertionError(field)
    return row


def _official_row(product: str, symbol: str, day: str, value: str, ordinal: int) -> dict[str, object]:
    schema = final_product_schema(product)
    row = _generic_row(schema)
    row.update(native_identity(symbol))
    start, end = subject._day_bounds(day)
    row["raw_object_ref"] = 0
    row["source_row_ordinal"] = ordinal
    if product == PRODUCT_BAR_1H:
        row.update({"venue_symbol": symbol, "open_time": end - 3_600_000,
                    "close_time": end - 1, "open": Decimal(value), "high": Decimal(value),
                    "low": Decimal(value), "close": Decimal(value)})
    elif product == PRODUCT_FUNDING_REALIZED:
        row.update({"venue_symbol": symbol, "calc_time": end - 1,
                    "funding_interval_hours": 8, "last_funding_rate": Decimal(value),
                    "long_cashflow_rate": -Decimal(value), "short_cashflow_rate": Decimal(value),
                    "cashflow_sign_convention": "long_pays_short_when_rate_positive"})
    else:
        row.update({"venue_symbol": symbol, "metric_symbol": symbol, "create_time": end - 300_000,
                    "sum_open_interest": Decimal(value), "gap_break_status": "continuous"})
    return row


def _official_root(tmp_path: Path, product: str, *, include_eth_oi: bool = False) -> subject.OfficialProductAuthority:
    root = tmp_path / f".{product}"
    descriptors: list[dict[str, object]] = []
    for symbol in subject.COMPARE_SYMBOLS:
        if product == PRODUCT_OPEN_INTEREST_5M and symbol == "ETHUSDT" and not include_eth_oi:
            continue
        for ordinal, day in enumerate(subject.COMPARE_DAYS):
            if product == PRODUCT_BAR_1H:
                value = str(100 + ordinal)
            elif product == PRODUCT_FUNDING_REALIZED:
                value = str(Decimal(ordinal + 1) / Decimal(100))
            else:
                value = str(100 + ordinal)
            row = _official_row(product, symbol, day, value, ordinal)
            schema = final_product_schema(product)
            table = pa.Table.from_pylist([row], schema=schema)
            parquet_path = root / ".partitions" / symbol / day[:7] / f"{day}.parquet"
            parquet_path.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(table, parquet_path)
            parquet_sha = hashlib.sha256(parquet_path.read_bytes()).hexdigest()
            lineage = {"document_type": f"{product}_partition_lineage", "required_product": product,
                       "parquet_sha256": parquet_sha, "raw_objects": [{"raw_object_ref": 0,
                       "source_key": f"raw/{product}/{symbol}/{day}", "source_sha256": "a" * 64}]}
            lineage_body = _json_bytes(lineage)
            lineage_sha = hashlib.sha256(lineage_body).hexdigest()
            lineage_path = root / ".lineage" / symbol / day[:7] / f"{lineage_sha}.json"
            _write(lineage_path, lineage_body)
            descriptors.append({"native_symbol": symbol, "utc_month": day[:7], "row_count": 1,
                                "parquet_path": str(parquet_path.relative_to(root)), "parquet_sha256": parquet_sha,
                                "lineage_path": str(lineage_path.relative_to(root)), "lineage_sha256": lineage_sha})
    completion = {"required_product": product, "schema_sha256": product_schema_identity(product), "partitions": descriptors}
    body = _json_bytes(completion)
    digest = hashlib.sha256(body).hexdigest()
    _write(root / ".complete" / f"{digest}.json", body)
    return subject.OfficialProductAuthority(product, root, digest, enforce_pinned_identity=False)


def _overlaps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[subject.OverlapReceipt, ...]:
    receipts: list[subject.OverlapReceipt] = []
    for endpoint in subject.OVERLAP:
        markets = []
        for symbol in subject.COMPARE_SYMBOLS:
            history = []
            for ordinal, day in enumerate(subject.COMPARE_DAYS):
                start, _ = subject._day_bounds(day)
                close = 100 + ordinal if endpoint != "/funding-rate-history" else ordinal + 1
                if endpoint == "/open-interest-history" and symbol == "BTCUSDT":
                    close += 5
                history.append({"t": start // 1000, "o": close, "h": close, "l": close, "c": close})
            markets.append({"symbol": f"{symbol}_PERP.A", "history": history})
        body = _json_bytes(markets)
        path = tmp_path / f"overlap-{endpoint[1:]}.json"
        digest, size = _write(path, body)
        retrieved = f"2026-08-22T22:54:5{len(receipts)}+00:00"
        monkeypatch.setitem(subject.OVERLAP, endpoint, (digest, size, retrieved))
        receipts.append(subject.OverlapReceipt(endpoint, path, digest, size, retrieved))
    return tuple(receipts)


def _authority_report(
    inventory_path: Path,
    inventory_sha: str,
    inventory_size: int,
) -> dict[str, object]:
    provenance: list[dict[str, object]] = [
        {
            "path": "/future-markets",
            "content_path": str(inventory_path),
            "sha256": inventory_sha,
            "byte_size": inventory_size,
            "params": {},
            "retrieved_at": "2026-08-22T22:54:17.555940+00:00",
            "status_code": 200,
        }
    ]
    for endpoint, (digest, size, retrieved) in subject.OVERLAP.items():
        provenance.append(
            {
                "path": endpoint,
                "content_path": f"cache/{digest}",
                "sha256": digest,
                "byte_size": size,
                "params": {
                    "from": "1577836800",
                    "interval": "daily",
                    "symbols": "BTCUSDT_PERP.A,ETHUSDT_PERP.A",
                    "to": "1609459200",
                },
                "retrieved_at": retrieved,
                "status_code": 200,
            }
        )
    return {
        "coinalyze": {
            "universe_support": {
                "supported_symbols": ["BTCUSDT"],
                "unmapped_symbols": ["MISSINGUSDT"],
                "supported_count": 1,
                "unmapped_count": 1,
                "universe_size": 2,
            },
            "provenance": provenance,
        },
        "product_matrix": [
            {
                "product": subject.PRODUCT,
                "accepted_universe_object_count": 0,
                "listed_bytes": 0,
                "listed_object_count": 0,
                "typed_gap_symbols": ["MISSINGUSDT"],
                "coverage_gap_kinds": ["coinalyze_symbol_unmapped"],
            }
        ],
    }


def _generation0_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, dict[str, object]]:
    inventory_rows = [
        {
            "exchange": "A",
            "is_perpetual": True,
            "symbol_on_exchange": "BTCUSDT",
            "symbol": "BTCUSDT_PERP.A",
            "base_asset": "BTC",
            "quote_asset": "USDT",
            "oi_lq_vol_denominated_in": "BASE_ASSET",
        },
        {
            "exchange": "A",
            "is_perpetual": True,
            "symbol_on_exchange": "AAVEUSD_PERP",
            "symbol": "AAVEUSD_PERP.A",
            "base_asset": "AAVE",
            "quote_asset": "USD",
            "oi_lq_vol_denominated_in": "QUOTE_ASSET",
        },
    ]
    inventory_body = _json_bytes(inventory_rows)
    inventory_sha = hashlib.sha256(inventory_body).hexdigest()
    content_root = tmp_path / "content"
    inventory_path = content_root / inventory_sha[:2] / inventory_sha
    _write(inventory_path, inventory_body)
    retained_path = tmp_path / "cache" / inventory_sha
    _write(retained_path, inventory_body)
    report = _authority_report(
        retained_path,
        inventory_sha,
        len(inventory_body),
    )
    mapping_digest = hashlib.sha256(
        subject.compact_json(
            [
                {
                    "native_symbol": "AAVEUSD_PERP",
                    "provider_symbol": "AAVEUSD_PERP.A",
                },
                {
                    "native_symbol": "BTCUSDT",
                    "provider_symbol": "BTCUSDT_PERP.A",
                },
            ]
        )
    ).hexdigest()
    inventory_plan = {
        "provider": "coinalyze",
        "identity": "coinalyze:/future-markets",
        "kind": "coinalyze_inventory",
        "payload": {
            "path": "/future-markets",
            "url": "https://api.coinalyze.net/v1/future-markets",
            "params": {},
            "accepted_digest": inventory_sha,
            "accepted_bytes": len(inventory_body),
            "accepted_path": str(tmp_path / "cache" / inventory_sha),
            "accepted_mappings": [
                {
                    "native_symbol": "BTCUSDT",
                    "provider_symbol": "BTCUSDT_PERP.A",
                }
            ],
            "inventory_mapping_digest": mapping_digest,
            "inventory_mapping_count": 2,
        },
    }
    params = {
        "symbols": "BTCUSDT_PERP.A",
        "interval": "daily",
        "from": "1609286400",
        "to": "1609459200",
        "convert_to_usd": "false",
    }
    query = subject.urlencode(params)
    liquidation_identity = f"/liquidation-history?{query}"
    liquidation_plan = {
        "provider": "coinalyze",
        "identity": liquidation_identity,
        "kind": "coinalyze_liquidation",
        "payload": {
            "path": "/liquidation-history",
            "query": query,
            "url": "https://api.coinalyze.net/v1/liquidation-history",
            "params": params,
            "native_symbol": "BTCUSDT",
            "provider_symbol": "BTCUSDT_PERP.A",
        },
    }
    liquidation_body = (
        b'[{"symbol":"BTCUSDT_PERP.A","history":['
        b'{"t":1609286400,"l":1,"s":0}]}]'
    )
    liquidation_sha = hashlib.sha256(liquidation_body).hexdigest()
    liquidation_path = content_root / liquidation_sha[:2] / liquidation_sha
    _write(liquidation_path, liquidation_body)
    state_path = tmp_path / "state.sqlite"
    connection = sqlite3.connect(state_path)
    connection.executescript(
        """
        CREATE TABLE plan_entry (
            provider TEXT, identity TEXT, kind TEXT, payload_json TEXT
        );
        CREATE TABLE completion (
            provider TEXT, identity TEXT, content_sha256 TEXT,
            content_path TEXT, listed_bytes INTEGER, retrieved_at TEXT,
            validation_state TEXT, revision_json TEXT,
            sidecar_sha256 TEXT, sidecar_path TEXT
        );
        CREATE TABLE sidecar_fact (provider TEXT);
        """
    )
    connection.execute(f"PRAGMA application_id={subject.STATE_APPLICATION_ID}")
    connection.execute(f"PRAGMA user_version={subject.STATE_USER_VERSION}")
    connection.execute(
        "INSERT INTO plan_entry VALUES (?,?,?,?)",
        (
            "coinalyze",
            "coinalyze:/future-markets",
            "coinalyze_inventory",
            json.dumps(inventory_plan),
        ),
    )
    connection.execute(
        "INSERT INTO completion VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            "coinalyze",
            "coinalyze:/future-markets",
            inventory_sha,
            str(inventory_path),
            len(inventory_body),
            "2026-08-22T22:54:17.555940+00:00",
            "retained_inventory",
            '{"retained":true}',
            None,
            None,
        ),
    )
    connection.execute(
        "INSERT INTO plan_entry VALUES (?,?,?,?)",
        (
            "coinalyze",
            liquidation_identity,
            "coinalyze_liquidation",
            json.dumps(liquidation_plan),
        ),
    )
    connection.execute(
        "INSERT INTO completion VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            "coinalyze",
            liquidation_identity,
            liquidation_sha,
            str(liquidation_path),
            len(liquidation_body),
            "2026-08-30T00:00:00+00:00",
            "checksum_verified",
            '{"points":1,"status":200}',
            None,
            None,
        ),
    )
    connection.commit()
    connection.close()
    monkeypatch.setattr(subject, "INVENTORY_SHA256", inventory_sha)
    monkeypatch.setattr(subject, "INVENTORY_BYTES", len(inventory_body))
    monkeypatch.setattr(subject, "INVENTORY_MAPPING_SHA256", mapping_digest)
    monkeypatch.setattr(subject, "ACCEPTED_RESPONSES", 1)
    monkeypatch.setattr(subject, "ACCEPTED_BINANCE_COMPLETIONS", 0)
    monkeypatch.setattr(subject, "ACCEPTED_SELECTED_MAPPINGS", 1)
    monkeypatch.setattr(subject, "ACCEPTED_UNMAPPED", 1)
    for name in (
        "authenticate_schema",
        "authenticate_domains",
        "authenticate_singletons",
        "authenticate_prefix",
        "_require_runnable_head",
    ):
        monkeypatch.setattr(subject.AcquisitionState, name, lambda self: None)
    monkeypatch.setattr(
        subject.AcquisitionState,
        "seal_head_row",
        lambda self: {"receipt_sha256": subject.GENERATION0_SEAL},
    )
    return state_path, content_root, report


def _officials(tmp_path: Path) -> tuple[subject.OfficialProductAuthority, ...]:
    return (_official_root(tmp_path, PRODUCT_BAR_1H), _official_root(tmp_path, PRODUCT_OPEN_INTEREST_5M),
            _official_root(tmp_path, PRODUCT_FUNDING_REALIZED))


def _normalize(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: subject.RawLiquidationObject, *, unmapped: tuple[str, ...] = ()) -> subject.LiquidationNormalizationResult:
    return subject.normalize_liquidation_sources(
        [raw], _mapping(raw), unmapped, _overlaps(tmp_path, monkeypatch), _officials(tmp_path),
        tmp_path / ".liquidation-output",
    )


def test_schema_exact_values_unicode_ordinals_and_month_ownership(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    start = 1_612_051_200  # 2021-01-31
    end = 1_612_137_600    # 2021-02-01
    raw = _raw(tmp_path, native="币安人生USDT", base="币安人生", start=start, end=end,
               points='[{"t":1612051200,"l":1.000000000000000001,"s":0.000000000000000001},{"t":1612137600,"l":2,"s":3}]')
    result = _normalize(tmp_path, monkeypatch, raw)
    assert result.schema_sha256 == "7a35b6abb2688ae6b2b79a187172d0a574a65da60f7829148fca13a4c0f794d6"
    assert [(p.native_symbol, p.utc_month) for p in result.partitions] == [("币安人生USDT", "2021-01"), ("币安人生USDT", "2021-02")]
    rows = [pq.read_table(p.parquet_path).to_pylist()[0] for p in result.partitions]
    assert rows[0]["point_ordinal"] == 0 and rows[1]["point_ordinal"] == 1
    assert rows[0]["long_liquidation"] == Decimal("1.000000000000000001")
    assert rows[0]["liquidation_imbalance"] == Decimal("1.000000000000000000")
    assert rows[1]["liquidation_imbalance"] == Decimal("-1.000000000000000000")
    assert rows[0]["provider_symbol"] == "币安人生USDT_PERP.A"
    assert rows[0]["source_interval_seconds"] == 86400
    assert rows[0]["observation_semantics"] == "censored_observed_daily_aggregate"
    assert rows[0]["event_complete"] is False
    assert rows[0]["canonical_instrument_id"] is None


def test_signed_max_precision_imbalance_ignores_decimal_context(
    tmp_path: Path,
) -> None:
    raw = _raw(
        tmp_path,
        start=1_609_286_400,
        end=1_609_372_800,
        points=(
            '[{"t":1609286400,"l":99999999999999999999.999999999999999999,'
            '"s":0.000000000000000001},'
            '{"t":1609372800,"l":0.000000000000000001,'
            '"s":99999999999999999999.999999999999999999}]'
        ),
    )
    records, _, _ = subject._parse_liquidation(raw)
    with localcontext() as context:
        context.prec = 3
        positive = subject._product_row(raw, records[0])["liquidation_imbalance"]
        negative = subject._product_row(raw, records[1])["liquidation_imbalance"]
    assert positive == Decimal("99999999999999999999.999999999999999998")
    assert negative == Decimal("-99999999999999999999.999999999999999998")


@pytest.mark.parametrize("points,message", [
    ('[{"t":1609286400,"l":true,"s":0}]', "exact JSON number"),
    ('[{"t":1609286400,"l":-1,"s":0}]', "negative"),
    ('[{"t":1609286401,"l":1,"s":0}]', "daily-grid"),
    ('[{"t":1609286400,"l":1e40,"s":0}]', "decimal"),
    ('[{"t":1609286400,"l":NaN,"s":0}]', "non-finite"),
    ('[{"t":1609286400,"l":1}]', "fields changed"),
])
def test_numeric_shape_and_point_refusals(tmp_path: Path, points: str, message: str) -> None:
    raw = _raw(tmp_path, start=1_609_286_400, end=1_609_286_400, points=points)
    with pytest.raises((subject.LiquidationNormalizationError, RuntimeError), match=message):
        subject._parse_liquidation(raw)


def test_identical_duplicate_collapses_and_conflict_refuses(tmp_path: Path) -> None:
    same = _raw(tmp_path, start=1_609_286_400, end=1_609_286_400,
                points='[{"t":1609286400,"l":1,"s":2},{"t":1609286400,"l":1,"s":2}]')
    rows, physical, collapsed = subject._parse_liquidation(same)
    assert (len(rows), physical, [x["collapsed_point_ordinal"] for x in collapsed]) == (1, 2, [1])
    conflict = _raw(tmp_path, start=1_609_286_400, end=1_609_286_400,
                    points='[{"t":1609286400,"l":1,"s":2},{"t":1609286400,"l":1,"s":3}]')
    with pytest.raises(subject.LiquidationNormalizationError, match="conflicts"):
        subject._parse_liquidation(conflict)


def test_missing_days_are_coalesced_zero_is_observed_and_whole_month_has_no_empty_parquet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    start = 1_609_459_200  # 2021-01-01
    end = 1_614_816_000    # 2021-03-04
    raw = _raw(tmp_path, start=start, end=end,
               points='[{"t":1609459200,"l":0,"s":0},{"t":1614816000,"l":1,"s":0}]')
    result = _normalize(tmp_path, monkeypatch, raw, unmapped=("UNMAPPEDUSDT",))
    assert result.product_rows == 2
    assert result.missing_daily_slots == ((end - start) // 86400 + 1) - 2
    assert {(p.utc_month, p.row_count) for p in result.partitions} == {("2021-01", 1), ("2021-03", 1)}
    assert not any(p.utc_month == "2021-02" for p in result.partitions)
    daily = [g for g in result.gaps if g.kind == "all_input_missing"]
    assert [g.row_count for g in daily] == [1, 1, 1]
    feb = next(g for g in daily if "/2021-02/" in str(g.parquet_path))
    gap = pq.read_table(feb.parquet_path).to_pylist()[0]
    assert gap["expected_grid_count"] == 28
    assert gap["gap_kind"] == "all_input_missing"
    assert result.authority_gap_rows == 1
    completion = json.loads(result.completion_path.read_text())
    assert completion["partition_calendar"]["gap_only_months"] == 1
    assert completion["source_semantics"]["censorship"]["known_from_utc_day"] == "2021-04-27"
    assert completion["source_semantics"]["censorship"]["before_state"] == "not_asserted_complete"


def test_comparison_exact_percentage_oi_difference_and_eth_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    document = subject.build_comparison(_overlaps(tmp_path, monkeypatch), _officials(tmp_path))
    assert len(document["entries"]) == 18
    prices = [x for x in document["entries"] if x["metric"] == "price_close"]
    funding = [x for x in document["entries"] if x["metric"] == "funding_rate"]
    btc_oi = [x for x in document["entries"] if x["metric"] == "open_interest" and x["symbol"] == "BTCUSDT"]
    eth_oi = [x for x in document["entries"] if x["metric"] == "open_interest" and x["symbol"] == "ETHUSDT"]
    assert {x["status"] for x in prices + funding} == {"exact_value_match"}
    assert funding[0]["secondary_fractional_value"] == {"numerator": "1", "denominator": "100"}
    assert all(x["official"]["funding_interval_hours"] == 8 for x in funding)
    assert all(x["official"]["timestamp_ms"] % 86_400_000 == 86_400_000 - 1 for x in funding)
    assert {tuple(x["difference"].values()) for x in btc_oi} == {("5", "1")}
    assert {x["status"] for x in btc_oi} == {"measured_difference"}
    assert {x["status"] for x in eth_oi} == {"official_overlap_unavailable"}
    assert all(x["difference"] is None and x["official"] is None for x in eth_oi)


def test_exact_comparison_ignores_ambient_decimal_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipts = _overlaps(tmp_path, monkeypatch)
    officials = _officials(tmp_path)
    with localcontext() as context:
        context.prec = 3
        low = subject.build_comparison(receipts, officials)
    with localcontext() as context:
        context.prec = 38
        high = subject.build_comparison(receipts, officials)
    assert _json_bytes(low) == _json_bytes(high)


def test_missing_official_partition_is_unavailable_but_tampered_file_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipts = _overlaps(tmp_path, monkeypatch)
    officials = list(_officials(tmp_path))
    doc = subject.build_comparison(receipts, officials)
    assert len([x for x in doc["entries"] if x["status"] == "official_overlap_unavailable"]) == 3
    bar = officials[0]
    completion_path = next((bar.root / ".complete").iterdir())
    completion = json.loads(completion_path.read_text())
    target = bar.root / completion["partitions"][0]["parquet_path"]
    target.write_bytes(b"tampered")
    with pytest.raises(subject.LiquidationNormalizationError, match="digest changed"):
        subject.build_comparison(receipts, officials)


@pytest.mark.parametrize("mutation", ["hash", "size", "time", "range", "symbols", "status"])
def test_overlap_receipt_envelope_refusal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    receipt = _overlaps(tmp_path, monkeypatch)[0]
    changes = {
        "hash": {"source_sha256": "0" * 64}, "size": {"byte_size": receipt.byte_size + 1},
        "time": {"retrieved_at": "2020-01-01T00:00:00+00:00"}, "range": {"request_from_s": receipt.request_from_s + 1},
        "symbols": {"symbols": "BTCUSDT_PERP.A"}, "status": {"status": 500},
    }
    with pytest.raises(subject.LiquidationNormalizationError, match="overlap"):
        subject._parse_overlap(replace(receipt, **changes[mutation]))


def test_raw_path_hash_size_and_query_binding_refusal(tmp_path: Path) -> None:
    raw = _raw(tmp_path)
    off_grid_to = raw.request_to_s + 1
    off_grid = replace(
        raw,
        identity=raw.identity.replace(
            f"to={raw.request_to_s}", f"to={off_grid_to}"
        ),
        request_to_s=off_grid_to,
    )
    for changed, message in (
        (replace(raw, source_sha256="0" * 64), "digest"),
        (replace(raw, byte_size=raw.byte_size + 1), "size"),
        (replace(raw, identity=raw.identity + "x"), "identity"),
        (off_grid, "daily grid"),
        (replace(raw, point_count=raw.point_count + 1), "point count"),
    ):
        with pytest.raises(subject.LiquidationNormalizationError, match=message):
            subject._validate_raw_descriptor(changed)
            subject._parse_liquidation(changed)
    raw.path.unlink()
    raw.path.symlink_to(tmp_path / "missing")
    with pytest.raises(subject.LiquidationNormalizationError, match="symlink"):
        subject._parse_liquidation(raw)


def test_inventory_strict_units_unicode_duplicates_and_mapping_digest(tmp_path: Path) -> None:
    market = {"exchange": "A", "is_perpetual": True, "symbol_on_exchange": "币安人生USDT",
              "symbol": "币安人生USDT_PERP.A", "base_asset": "币安人生", "quote_asset": "USDT",
              "oi_lq_vol_denominated_in": "BASE_ASSET"}
    coin_margined = {
        "exchange": "A",
        "is_perpetual": True,
        "symbol_on_exchange": "AAVEUSD_PERP",
        "symbol": "AAVEUSD_PERP.A",
        "base_asset": "AAVE",
        "quote_asset": "USD",
        "oi_lq_vol_denominated_in": "QUOTE_ASSET",
    }
    body = _json_bytes([market, coin_margined])
    mappings, markets, perpetuals, digest = subject._inventory_mappings(body, {"币安人生USDT"})
    assert (markets, perpetuals, mappings["币安人生USDT"].base_asset) == (
        2,
        2,
        "币安人生",
    )
    expected_pairs = [
        {"native_symbol": "AAVEUSD_PERP", "provider_symbol": "AAVEUSD_PERP.A"},
        {
            "native_symbol": "币安人生USDT",
            "provider_symbol": "币安人生USDT_PERP.A",
        },
    ]
    assert digest == hashlib.sha256(subject.compact_json(expected_pairs)).hexdigest()
    wrong = dict(market, oi_lq_vol_denominated_in="USD")
    with pytest.raises(subject.LiquidationNormalizationError, match="base asset"):
        subject._inventory_mappings(
            _json_bytes([wrong, coin_margined]), {"币安人生USDT"}
        )
    with pytest.raises(subject.LiquidationNormalizationError, match="repeats"):
        subject._inventory_mappings(_json_bytes([market, market]), {"币安人生USDT"})


def test_report_and_generation0_loader_accept_actual_identity_shapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path, content_root, report = _generation0_authority(
        tmp_path, monkeypatch
    )
    mapped, unmapped, receipts = subject._report_authority(report)
    assert mapped == {"BTCUSDT"}
    assert unmapped == ("MISSINGUSDT",)
    assert {receipt.endpoint for receipt in receipts} == set(subject.OVERLAP)
    sources, mappings, loaded_unmapped, inventory = (
        subject.load_generation0_authority(state_path, content_root, report)
    )
    assert len(sources) == 1
    assert sources[0].identity.startswith("/liquidation-history?")
    assert not sources[0].identity.startswith("coinalyze:")
    assert mappings["BTCUSDT"].base_asset == "BTC"
    assert loaded_unmapped == ("MISSINGUSDT",)
    assert inventory.mapping_count == 2


def test_report_parser_refuses_unmapped_and_receipt_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path, _content_root, report = _generation0_authority(
        tmp_path, monkeypatch
    )
    assert state_path.exists()
    changed_gap = json.loads(json.dumps(report))
    changed_gap["product_matrix"][0]["typed_gap_symbols"] = []
    with pytest.raises(subject.LiquidationNormalizationError, match="authority gaps"):
        subject._report_authority(changed_gap)
    changed_receipt = json.loads(json.dumps(report))
    changed_receipt["coinalyze"]["provenance"][1]["status_code"] = 500
    with pytest.raises(subject.LiquidationNormalizationError, match="retrieval changed"):
        subject._report_authority(changed_receipt)


def test_generation0_loader_refuses_query_appended_payload_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path, content_root, report = _generation0_authority(
        tmp_path, monkeypatch
    )
    connection = sqlite3.connect(state_path)
    row = connection.execute(
        "SELECT identity,payload_json FROM plan_entry "
        "WHERE kind='coinalyze_liquidation'"
    ).fetchone()
    assert row is not None
    identity, payload_json = row
    envelope = json.loads(payload_json)
    envelope["payload"]["url"] += "?" + envelope["payload"]["query"]
    connection.execute(
        "UPDATE plan_entry SET payload_json=? WHERE identity=?",
        (json.dumps(envelope), identity),
    )
    connection.commit()
    connection.close()
    with pytest.raises(
        subject.LiquidationNormalizationError,
        match="liquidation request identity changed",
    ):
        subject.load_generation0_authority(state_path, content_root, report)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("accepted_path", "/wrong/path", "retained receipt binding"),
        ("accepted_digest", "0" * 64, "retained-content binding"),
    ],
)
def test_generation0_loader_refuses_inventory_plan_binding_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
    message: str,
) -> None:
    state_path, content_root, report = _generation0_authority(
        tmp_path, monkeypatch
    )
    connection = sqlite3.connect(state_path)
    row = connection.execute(
        "SELECT identity,payload_json FROM plan_entry "
        "WHERE kind='coinalyze_inventory'"
    ).fetchone()
    assert row is not None
    identity, payload_json = row
    envelope = json.loads(payload_json)
    envelope["payload"][field] = value
    connection.execute(
        "UPDATE plan_entry SET payload_json=? WHERE identity=?",
        (json.dumps(envelope), identity),
    )
    connection.commit()
    connection.close()
    with pytest.raises(subject.LiquidationNormalizationError, match=message):
        subject.load_generation0_authority(state_path, content_root, report)


@pytest.mark.parametrize(
    ("target", "field", "value", "message"),
    [
        (
            "inventory",
            "revision_json",
            '{"retained":false}',
            "inventory completion state changed",
        ),
        (
            "inventory",
            "retrieved_at",
            "2020-01-01T00:00:00+00:00",
            "retained receipt binding",
        ),
        (
            "liquidation",
            "revision_json",
            '{"points":1,"status":"200"}',
            "completion status changed",
        ),
        (
            "liquidation",
            "sidecar_sha256",
            "a" * 64,
            "sidecar fields",
        ),
        (
            "liquidation",
            "content_path",
            "/wrong/content",
            "content-address path changed",
        ),
    ],
)
def test_generation0_loader_refuses_completion_envelope_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    field: str,
    value: object,
    message: str,
) -> None:
    state_path, content_root, report = _generation0_authority(
        tmp_path, monkeypatch
    )
    kind = (
        "coinalyze_inventory"
        if target == "inventory"
        else "coinalyze_liquidation"
    )
    connection = sqlite3.connect(state_path)
    identity = connection.execute(
        "SELECT identity FROM plan_entry WHERE kind=?", (kind,)
    ).fetchone()[0]
    connection.execute(
        f"UPDATE completion SET {field}=? WHERE identity=?",
        (value, identity),
    )
    connection.commit()
    connection.close()
    with pytest.raises(subject.LiquidationNormalizationError, match=message):
        subject.load_generation0_authority(state_path, content_root, report)


def test_generation0_loader_refuses_coinalyze_sidecar_fact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path, content_root, report = _generation0_authority(
        tmp_path, monkeypatch
    )
    connection = sqlite3.connect(state_path)
    connection.execute("INSERT INTO sidecar_fact VALUES ('coinalyze')")
    connection.commit()
    connection.close()
    with pytest.raises(subject.LiquidationNormalizationError, match="sidecar fact"):
        subject.load_generation0_authority(state_path, content_root, report)


def test_strict_json_duplicate_key_and_decoder_float_refusal() -> None:
    with pytest.raises(subject.LiquidationNormalizationError, match="repeats"):
        subject._strict_json(b'{"a":1,"a":1}', maximum=100)
    value = subject._strict_json(b'{"a":1.25}', maximum=100)
    assert type(value["a"]) is Decimal
    with pytest.raises(subject.LiquidationNormalizationError, match="exact JSON number"):
        subject._decimal(1.25, key="test", column="long_liquidation", row=0)


def test_unmapped_gap_is_separate_from_daily_gap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = _raw(tmp_path)
    result = _normalize(tmp_path, monkeypatch, raw, unmapped=("MISSING1", "MISSING2"))
    authority = next(x for x in result.gaps if x.kind == "coinalyze_symbol_unmapped")
    rows = pq.read_table(authority.parquet_path).to_pylist()
    assert {x["native_symbol"] for x in rows} == {"MISSING1", "MISSING2"}
    assert all(x["utc_month"] == "authority" and x["expected_grid_count"] == 0 for x in rows)
    assert any(x.kind == "all_input_missing" for x in result.gaps)


def test_replay_is_deterministic_and_completion_is_last(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = _raw(tmp_path)
    receipts = _overlaps(tmp_path, monkeypatch)
    officials = _officials(tmp_path)
    first = subject.normalize_liquidation_sources([raw], _mapping(raw), (), receipts, officials, tmp_path / ".out")
    second = subject.normalize_liquidation_sources([raw], _mapping(raw), (), receipts, officials, tmp_path / ".out")
    assert first.completion_sha256 == second.completion_sha256
    assert second.completion_reused is True
    assert all(p.reused for p in second.partitions)
    assert len(list((tmp_path / ".out" / ".complete").iterdir())) == 1


def test_interruption_leaves_no_completion_and_resume_uses_same_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = _raw(tmp_path)
    receipts = _overlaps(tmp_path, monkeypatch)
    officials = _officials(tmp_path)
    def stop(kind: str, _staged: Path, _destination: Path) -> None:
        if kind == "lineage":
            raise RuntimeError("interrupt")
    with pytest.raises(RuntimeError, match="interrupt"):
        subject.normalize_liquidation_sources([raw], _mapping(raw), (), receipts, officials, tmp_path / ".out", hooks=subject.PublicationHooks(stop))
    completion = tmp_path / ".out" / ".complete"
    assert not completion.exists() or not list(completion.iterdir())
    resumed = subject.normalize_liquidation_sources([raw], _mapping(raw), (), receipts, officials, tmp_path / ".out")
    assert resumed.product_rows == 2


def test_root_lock_refuses_concurrent_writer(tmp_path: Path) -> None:
    root = tmp_path / ".out"
    held = subject._OutputTree(root)
    try:
        with pytest.raises(subject.LiquidationNormalizationError, match="holds output root"):
            subject._OutputTree(root)
    finally:
        held.close()


@pytest.mark.parametrize("attack", ["stage", "winner", "root"])
def test_publication_substitution_cannot_produce_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    raw = _raw(tmp_path)
    output = tmp_path / ".attacked"
    fired = False

    def substitute(kind: str, staged: Path, destination: Path) -> None:
        nonlocal fired
        if fired or kind != "comparison":
            return
        fired = True
        if attack == "stage":
            staged.unlink()
            staged.write_bytes(b"replacement")
        elif attack == "winner":
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"replacement")
        else:
            moved = tmp_path / ".moved-held-root"
            output.rename(moved)
            output.mkdir()

    with pytest.raises(subject.LiquidationNormalizationError):
        subject.normalize_liquidation_sources(
            [raw],
            _mapping(raw),
            (),
            _overlaps(tmp_path, monkeypatch),
            _officials(tmp_path),
            output,
            hooks=subject.PublicationHooks(substitute),
        )
    assert fired
    completion = output / ".complete"
    assert not completion.exists() or not list(completion.iterdir())


def test_official_parquet_is_consumed_through_authenticated_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipts = _overlaps(tmp_path, monkeypatch)
    officials = _officials(tmp_path)
    original = subject.pq.ParquetFile
    opened: list[str] = []

    def capture(where: object, *args: object, **kwargs: object) -> object:
        opened.append(str(where))
        return original(where, *args, **kwargs)

    monkeypatch.setattr(subject.pq, "ParquetFile", capture)
    document = subject.build_comparison(receipts, officials)
    assert len(document["entries"]) == 18
    assert opened
    assert all(path.startswith("/proc/self/fd/") for path in opened)


def test_multi_month_typed_buffers_are_released_before_next_month(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    points = (
        '[{"t":1609459200,"l":1,"s":0},'
        '{"t":1612051200,"l":2,"s":0},'
        '{"t":1612137600,"l":3,"s":0},'
        '{"t":1614470400,"l":4,"s":0},'
        '{"t":1614556800,"l":5,"s":0},'
        '{"t":1614643200,"l":6,"s":0}]'
    )
    raw = _raw(
        tmp_path,
        start=1_609_459_200,
        end=1_614_643_200,
        points=points,
    )
    original = subject._product_row
    references: list[weakref.ReferenceType[dict[str, object]]] = []
    alive_at_partition: list[int] = []
    alive_during_build: list[int] = []
    month_sizes: list[int] = []

    class TrackedRow(dict[str, object]):
        pass

    def tracked(
        source: subject.RawLiquidationObject, record: dict[str, object]
    ) -> dict[str, object]:
        row = TrackedRow(original(source, record))
        references.append(weakref.ref(row))
        alive_during_build.append(sum(ref() is not None for ref in references))
        return row

    def before_publish(kind: str, _staged: Path, _destination: Path) -> None:
        if kind == "partition":
            alive_at_partition.append(sum(ref() is not None for ref in references))

    def observe_buffer(_symbol: str, _month: str, rows: int) -> None:
        month_sizes.append(rows)

    monkeypatch.setattr(subject, "_product_row", tracked)
    result = subject.normalize_liquidation_sources(
        [raw],
        _mapping(raw),
        (),
        _overlaps(tmp_path, monkeypatch),
        _officials(tmp_path),
        tmp_path / ".bounded",
        hooks=subject.PublicationHooks(before_publish, observe_buffer),
    )
    assert result.product_rows == 6
    assert month_sizes == [2, 2, 2]
    assert alive_during_build == [1, 2, 1, 2, 1, 2]
    assert alive_at_partition == [2, 2, 2]


def test_existing_different_completion_blocks_no_clobber(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / ".out"
    (root / ".complete").mkdir(parents=True)
    (root / ".complete" / ("f" * 64 + ".json")).write_text("{}")
    raw = _raw(tmp_path)
    with pytest.raises(subject.LiquidationNormalizationError, match="another completion"):
        subject.normalize_liquidation_sources([raw], _mapping(raw), (), _overlaps(tmp_path, monkeypatch), _officials(tmp_path), root)


def test_official_lineage_hash_and_binding_refusal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipts = _overlaps(tmp_path, monkeypatch)
    officials = list(_officials(tmp_path))
    bar = officials[0]
    completion = json.loads(next((bar.root / ".complete").iterdir()).read_text())
    lineage = bar.root / completion["partitions"][0]["lineage_path"]
    lineage.write_text('{}\n')
    with pytest.raises(subject.LiquidationNormalizationError, match="digest changed"):
        subject.build_comparison(receipts, officials)


def test_missing_official_physical_partition_never_becomes_zero_or_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipts = _overlaps(tmp_path, monkeypatch)
    officials = list(_officials(tmp_path))
    bar = officials[0]
    completion = json.loads(next((bar.root / ".complete").iterdir()).read_text())
    (bar.root / completion["partitions"][0]["parquet_path"]).unlink()
    with pytest.raises(subject.LiquidationNormalizationError, match="opened"):
        subject.build_comparison(receipts, officials)


def test_safe_component_preserves_unicode_and_refuses_traversal() -> None:
    assert subject._safe_component("币安人生USDT") == "币安人生USDT"
    for value in ("", ".", "..", "../BTCUSDT", "BTC/USDT", "BTC\\USDT", "x\x00y"):
        with pytest.raises(subject.LiquidationNormalizationError, match="unsafe"):
            subject._safe_component(value)
