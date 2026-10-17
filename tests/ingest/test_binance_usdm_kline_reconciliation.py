"""Temporary-fixture tests for bounded one-minute and hourly reconciliation."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from dataclasses import dataclass, field, replace
from decimal import Decimal, localcontext
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.acquisition import binance_usdm_kline_comparison_sample as sample
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    PRODUCT_BAR_1H,
    PRODUCT_TRADE_FLOW_1H,
    QUALITY_GAP_COLUMNS,
    final_product_schema,
    native_identity,
    product_schema_identity,
)
from cryptofactors.ingest import binance_usdm_kline_reconciliation as rec

RETRIEVAL = "ZZ-RETRIEVAL-7f3a"
SCALE = 10**18
BAR = PRODUCT_BAR_1H
FLOW = PRODUCT_TRADE_FLOW_1H
FIELD_CASES = [(BAR, name) for name in rec.BAR_FIELDS] + [(FLOW, name) for name in rec.FLOW_FIELDS]


@dataclass
class Hour:
    index: int = 0
    count: int = 60
    tokens: dict[str, str] | None = None
    rows: list[list[str]] | None = None
    duplicate_first: bool = False
    reverse_file: bool = False
    bar: bool = True
    flow: bool = True
    bar_override: dict[str, int] | None = None
    flow_override: dict[str, int] | None = None
    bar_close_delta: int = 0
    flow_close_delta: int = 0


@dataclass
class Gap:
    product: str
    hour_index: int
    kind: str
    reason: str
    exclusion: bool = False
    start_ms: int | None = None
    end_ms: int | None = None


@dataclass
class Day:
    symbol: str
    utc_date: str
    roles: tuple[str, ...]
    hours: tuple[Hour, ...] = field(default_factory=lambda: (Hour(),))
    header: bool = False
    gaps: tuple[Gap, ...] = ()
    bad_foreign: bool = False
    duplicate_open: bool = False


@dataclass
class World:
    policy: sample.Policy
    evidence: Path
    output: Path
    repo: Path
    proofs: dict[str, dict[str, str]]
    roots: dict[str, Path]


def _dec(unscaled: int) -> Decimal:
    if unscaled == 0:
        return Decimal((0, (0,), -18))
    sign = 1 if unscaled < 0 else 0
    digits = tuple(int(character) for character in str(abs(unscaled)))
    return Decimal((sign, digits, -18))


def _lex(token: str) -> int:
    negative = token.startswith("-")
    body = token[1:] if token[:1] in "+-" else token
    whole, _, frac = body.partition(".")
    whole = whole or "0"
    digits = whole + frac + ("0" * (18 - len(frac)))
    value = int(digits)
    return -value if negative else value


def _minute(open_ms: int, tokens: dict[str, str] | None = None) -> list[str]:
    values = {
        "open_time": str(open_ms),
        "open": "100",
        "high": "100",
        "low": "100",
        "close": "100",
        "volume": "1",
        "close_time": str(open_ms + 59_999),
        "quote_volume": "100",
        "count": "1",
        "taker_buy_volume": "0.4",
        "taker_buy_quote_volume": "40",
        "ignore": "7",
    }
    if tokens:
        values.update(tokens)
    return [values[name] for name in sample.MINUTE_FIELDS]


def _primaries(rows: list[list[str]]) -> list[list[str]]:
    grouped: dict[str, list[str]] = {}
    for row in rows:
        current = grouped.get(row[0])
        if current is None:
            grouped[row[0]] = row
        else:
            assert current == row
    return [grouped[key] for key in sorted(grouped, key=int)]


def _aggregate(rows: list[list[str]]) -> dict[str, int]:
    chosen = _primaries(rows)
    index = {name: position for position, name in enumerate(sample.MINUTE_FIELDS)}

    def column(name: str) -> list[str]:
        return [row[index[name]] for row in chosen]

    volume = sum(_lex(token) for token in column("volume"))
    quote = sum(_lex(token) for token in column("quote_volume"))
    buy = sum(_lex(token) for token in column("taker_buy_volume"))
    buy_quote = sum(_lex(token) for token in column("taker_buy_quote_volume"))
    sell = volume - buy
    sell_quote = quote - buy_quote
    return {
        "open": _lex(chosen[0][index["open"]]),
        "high": max(_lex(token) for token in column("high")),
        "low": min(_lex(token) for token in column("low")),
        "close": _lex(chosen[-1][index["close"]]),
        "volume": volume,
        "quote_volume": quote,
        "trade_count": sum(int(token) for token in column("count")),
        "taker_buy_volume": buy,
        "taker_buy_quote_volume": buy_quote,
        "taker_sell_volume": sell,
        "taker_sell_quote_volume": sell_quote,
        "volume_imbalance": buy - sell,
        "quote_volume_imbalance": buy_quote - sell_quote,
    }


def _apply(values: dict[str, int], override: dict[str, int] | None) -> dict[str, int]:
    merged = dict(values)
    if override:
        merged.update(override)
    return merged


def _product_row(product: str, symbol: str, open_time: int, values: dict[str, int], close_delta: int) -> dict:
    close_time = open_time + rec.HOUR_CLOSE + close_delta
    identity = native_identity(symbol)
    shared = {
        "raw_object_ref": 0,
        "source_row_ordinal": 0,
        "venue_symbol": symbol,
        "open_time": open_time,
        "close_time": close_time,
        "volume": _dec(values["volume"]),
        "quote_volume": _dec(values["quote_volume"]),
        "trade_count": values["trade_count"],
    }
    if product == BAR:
        return {
            **shared,
            "open": _dec(values["open"]),
            "high": _dec(values["high"]),
            "low": _dec(values["low"]),
            "close": _dec(values["close"]),
            "source_reserved": 0,
            **identity,
        }
    return {
        **shared,
        "taker_buy_volume": _dec(values["taker_buy_volume"]),
        "taker_buy_quote_volume": _dec(values["taker_buy_quote_volume"]),
        **identity,
        "taker_sell_volume": _dec(values["taker_sell_volume"]),
        "taker_sell_quote_volume": _dec(values["taker_sell_quote_volume"]),
        "volume_imbalance": _dec(values["volume_imbalance"]),
        "quote_volume_imbalance": _dec(values["quote_volume_imbalance"]),
    }


def _parquet(rows: list[dict], schema: pa.Schema) -> bytes:
    if rows:
        table = pa.Table.from_pylist(rows, schema=schema)
    else:
        table = pa.table({item.name: pa.array([], type=item.type) for item in schema}, schema=schema)
    buffer = io.BytesIO()
    pq.write_table(table, buffer)
    return buffer.getvalue()


def _write_hashed(root: Path, folder: str, suffix: str, body: bytes) -> tuple[str, str]:
    digest = sample.sha256_hex(body)
    relative = f"{folder}/{digest}{suffix}"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return digest, relative


def _exclusion_sha(rows: list[dict]) -> str:
    hasher = hashlib.sha256()
    for row in rows:
        hasher.update(sample.canonical_json(row))
    return hasher.hexdigest()


def _gap_schema() -> pa.Schema:
    return pa.schema([column.field() for column in QUALITY_GAP_COLUMNS])


def _schema_facts(schema: pa.Schema) -> list[dict[str, object]]:
    return [{"name": item.name, "nullable": item.nullable, "type": str(item.type)} for item in schema]


def _zip_bytes(member: str, rows: list[list[str]], header: bool) -> bytes:
    lines = [",".join(sample.MINUTE_FIELDS)] if header else []
    lines.extend(",".join(row) for row in rows)
    payload = ("\n".join(lines) + "\n").encode()
    buffer = io.BytesIO()
    with __import__("zipfile").ZipFile(buffer, "w", compression=__import__("zipfile").ZIP_DEFLATED) as archive:
        archive.writestr(member, payload)
    return buffer.getvalue()


def _hour_rows(day: Day, hour: Hour, start: int) -> list[list[str]]:
    hour_open = start + hour.index * rec.HOUR_MS
    if hour.rows is not None:
        rows = list(hour.rows)
    else:
        rows = [_minute(hour_open + index * rec.MINUTE_MS, hour.tokens) for index in range(hour.count)]
    if hour.duplicate_first and rows:
        rows.append(list(rows[0]))
    if hour.reverse_file:
        rows.reverse()
    return rows


def assemble(tmp_path: Path, days: tuple[Day, ...] | list[Day], *, reverse_products: bool = False) -> World:
    repo = tmp_path / "repo"
    evidence = tmp_path / "evidence"
    output = tmp_path / "output"
    roots = {BAR: repo / "products" / "bar", FLOW: repo / "products" / "flow"}
    product_rows: dict[str, dict[tuple[str, str], list[dict]]] = {BAR: {}, FLOW: {}}
    gap_rows: dict[str, list[dict]] = {BAR: [], FLOW: []}
    exclusions: dict[str, list[dict]] = {BAR: [], FLOW: []}
    bodies: dict[str, bytes] = {}
    records: list[dict[str, object]] = []
    roles: list[sample.Role] = []
    for day in days:
        start = sample.utc_day_start_ms(day.utc_date)
        month = day.utc_date[:7]
        zip_rows: list[list[str]] = []
        for hour in day.hours:
            rows = _hour_rows(day, hour, start)
            zip_rows.extend(rows)
            if not (hour.bar or hour.flow):
                continue
            values = _aggregate(rows)
            hour_open = start + hour.index * rec.HOUR_MS
            for product, enabled, override, delta in (
                (BAR, hour.bar, hour.bar_override, hour.bar_close_delta),
                (FLOW, hour.flow, hour.flow_override, hour.flow_close_delta),
            ):
                if not enabled:
                    continue
                product_rows[product].setdefault((day.symbol, month), []).append(
                    _product_row(product, day.symbol, hour_open, _apply(values, override), delta)
                )
        for gap in day.gaps:
            hour_open = start + gap.hour_index * rec.HOUR_MS
            begin = hour_open if gap.start_ms is None else gap.start_ms
            end = hour_open if gap.end_ms is None else gap.end_ms
            gap_rows[gap.product].append(
                {
                    **native_identity(day.symbol),
                    "required_product": gap.product,
                    "utc_month": sample.utc_year_month(begin),
                    "missing_run_start_ms": begin,
                    "missing_run_end_ms": end,
                    "expected_grid_count": (end - begin) // rec.HOUR_MS + 1,
                    "gap_kind": gap.kind,
                    "reason": gap.reason,
                }
            )
            if gap.exclusion:
                exclusions[gap.product].append(
                    {
                        "failed_invariant_flags": {"total_volume_pair_inconsistent": True},
                        "native_symbol": day.symbol,
                        "open_time": hour_open,
                        "reason": gap.reason,
                        "required_product": gap.product,
                        "source_key": "data/futures/um/monthly/klines/not-the-sample.zip",
                        "source_row_ordinal": 0,
                        "source_sha256": sample.sha256_hex(day.symbol.encode()),
                        "utc_month": month,
                    }
                )
        if day.bad_foreign:
            foreign = start + rec.DAY_MS
            product_rows[BAR].setdefault((day.symbol, month), []).append(
                _product_row(BAR, day.symbol, foreign, _aggregate([_minute(start)]), 1)
            )
        if day.duplicate_open:
            for product in (BAR, FLOW):
                bucket = product_rows[product].get((day.symbol, month), [])
                if bucket:
                    bucket.append(dict(bucket[0]))
        member = sample.minute_member_name(day.symbol, day.utc_date)
        key = sample.minute_object_key(day.symbol, day.utc_date)
        payload = _zip_bytes(member, zip_rows, day.header)
        digest = sample.sha256_hex(payload)
        basename = key.rsplit("/", 1)[-1]
        bodies[sample.official_object_url(key)] = payload
        bodies[sample.official_object_url(key + ".CHECKSUM")] = f"{digest}  {basename}\n".encode()
        hourly = sample.sha256_hex(f"{day.symbol}|{day.utc_date}".encode())
        hourly_key = sample.hourly_object_key(day.symbol, day.utc_date)
        for regime in day.roles:
            roles.append(sample.Role(day.symbol, day.utc_date, regime))
            records.append(
                {
                    "byte_size": 128,
                    "checksum_match": True,
                    "family": "daily/klines",
                    "key": hourly_key,
                    "products": ["binance_usdm_bar_1h"],
                    "provider_checksum": hourly,
                    "regime": regime,
                    "sha256": hourly,
                    "symbol": day.symbol,
                    "url": sample.official_object_url(hourly_key),
                }
            )
    proofs: dict[str, dict[str, str]] = {}
    completions: dict[str, str] = {}
    gap_schema = _gap_schema()
    for product, root in roots.items():
        partitions = []
        for symbol, month in sorted(product_rows[product]):
            rows = product_rows[product][(symbol, month)]
            if reverse_products:
                rows = list(reversed(rows))
            schema = final_product_schema(product)
            parquet_sha, parquet_path = _write_hashed(
                root, f".partitions/{symbol}/{month}", ".parquet", _parquet(rows, schema)
            )
            lineage = {
                "document_type": f"{product}_partition_lineage",
                "native_symbol": symbol,
                "parquet_sha256": parquet_sha,
                "raw_objects": [
                    {
                        "byte_size": 10,
                        "checksum_authority": "sha256",
                        "raw_object_ref": 0,
                        "retrieval_time": "LINEAGE-NOT-SAMPLE",
                        "source_availability_state": sample.UNKNOWN_AVAILABILITY,
                        "source_available_at": None,
                        "source_key": f"data/futures/um/monthly/klines/{symbol}/1h/{symbol}-1h-{month}.zip",
                        "source_sha256": sample.sha256_hex(f"{symbol}|{month}".encode()),
                        "validation_state": "accepted",
                    }
                ],
                "required_product": product,
                "row_count": len(rows),
                "schema_sha256": product_schema_identity(product),
                "schema_version": 2,
                "utc_month": month,
            }
            lineage_sha, lineage_path = _write_hashed(
                root, f".lineage/{symbol}/{month}", ".json", sample.canonical_json(lineage)
            )
            partitions.append(
                {
                    "lineage_path": lineage_path,
                    "lineage_sha256": lineage_sha,
                    "native_symbol": symbol,
                    "parquet_path": parquet_path,
                    "parquet_sha256": parquet_sha,
                    "row_count": len(rows),
                    "utc_month": month,
                }
            )
        # A selected day with no hourly rows still needs its symbol-month partition.
        for day in days:
            key = (day.symbol, day.utc_date[:7])
            if key in product_rows[product]:
                continue
            product_rows[product][key] = []
            schema = final_product_schema(product)
            parquet_sha, parquet_path = _write_hashed(
                root, f".partitions/{day.symbol}/{day.utc_date[:7]}", ".parquet", _parquet([], schema)
            )
            lineage = {
                "document_type": f"{product}_partition_lineage",
                "native_symbol": day.symbol,
                "parquet_sha256": parquet_sha,
                "raw_objects": [
                    {
                        "byte_size": 10,
                        "checksum_authority": "sha256",
                        "raw_object_ref": 0,
                        "retrieval_time": "LINEAGE-NOT-SAMPLE",
                        "source_availability_state": sample.UNKNOWN_AVAILABILITY,
                        "source_available_at": None,
                        "source_key": "data/futures/um/monthly/klines/empty.zip",
                        "source_sha256": sample.sha256_hex(b"empty-partition"),
                        "validation_state": "accepted",
                    }
                ],
                "required_product": product,
                "row_count": 0,
                "schema_sha256": product_schema_identity(product),
                "schema_version": 2,
                "utc_month": day.utc_date[:7],
            }
            lineage_sha, lineage_path = _write_hashed(
                root,
                f".lineage/{day.symbol}/{day.utc_date[:7]}",
                ".json",
                sample.canonical_json(lineage),
            )
            partitions.append(
                {
                    "lineage_path": lineage_path,
                    "lineage_sha256": lineage_sha,
                    "native_symbol": day.symbol,
                    "parquet_path": parquet_path,
                    "parquet_sha256": parquet_sha,
                    "row_count": 0,
                    "utc_month": day.utc_date[:7],
                }
            )
        exclusion_digest = _exclusion_sha(exclusions[product])
        gap_sha, gap_path = _write_hashed(
            root, ".quality-gaps", ".parquet", _parquet(gap_rows[product], gap_schema)
        )
        gap_lineage = {
            "document_type": f"{product}_quality_gap_lineage",
            "missing_grid_points": sum(int(row["expected_grid_count"]) for row in gap_rows[product]),
            "provider_invalid_exclusion_count": len(exclusions[product]),
            "provider_invalid_exclusions": exclusions[product],
            "provider_invalid_exclusions_sha256": exclusion_digest,
            "quality_gap_parquet_sha256": gap_sha,
            "quality_gap_schema": _schema_facts(gap_schema),
            "required_product": product,
            "row_count": len(gap_rows[product]),
            "schema_version": 2,
        }
        gap_lineage_sha, gap_lineage_path = _write_hashed(
            root, ".quality-gap-lineage", ".json", sample.canonical_json(gap_lineage)
        )
        proofs[product] = {
            "exclusions": exclusion_digest,
            "lineage": gap_lineage_sha,
            "parquet": gap_sha,
        }
        completion = {
            "document_type": f"{product}_product_completion",
            "partitions": partitions,
            "quality_gap_artifact": {
                "lineage_path": gap_lineage_path,
                "lineage_sha256": gap_lineage_sha,
                "missing_grid_points": gap_lineage["missing_grid_points"],
                "parquet_path": gap_path,
                "parquet_sha256": gap_sha,
                "row_count": len(gap_rows[product]),
            },
            "required_product": product,
            "schema_sha256": product_schema_identity(product),
            "schema_version": 2,
        }
        body = sample.canonical_json(completion)
        completion_sha = sample.sha256_hex(body)
        marker = root / ".complete" / f"{completion_sha}.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_bytes(body)
        completions[product] = completion_sha
    report = sample.canonical_json({"samples": records})
    report_sha = sample.sha256_hex(report)
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "qualification.json").write_bytes(report)
    policy = sample.Policy(
        repo=repo,
        report_relative="qualification.json",
        report_sha256=report_sha,
        bar_root="products/bar",
        bar_completion=completions[BAR],
        flow_root="products/flow",
        flow_completion=completions[FLOW],
        protected=("qualification.json", "products/bar", "products/flow", "generation0"),
        roles=tuple(roles),
    )
    sample.fetch_sample(
        policy,
        evidence,
        fetch=True,
        transport=_Transport(bodies),
        clock=lambda: RETRIEVAL,
    )
    return World(policy, evidence, output, repo, proofs, roots)


class _Transport:
    def __init__(self, bodies: dict[str, bytes]):
        self.bodies = bodies
        self.calls: list[str] = []

    def fetch(self, url: str, *, timeout: float, max_bytes: int) -> sample.FetchResponse:
        self.calls.append(url)
        body = self.bodies[url]
        return sample.FetchResponse(200, url, body, len(body))


def _run(world: World, output: Path | None = None):
    result = rec.reconcile(world.policy, world.evidence, output or world.output)
    report = json.loads(result.report_path.read_text())
    return result, report


def _no_marker(path: Path) -> None:
    complete = path / ".complete"
    assert not complete.exists() or not any(complete.iterdir())


def _counts(day: dict) -> dict[str, int]:
    counts = {"complete": 0, "partial": 0, "zero_observation": 0}
    assert day["expected_hour_count"] == 24
    assert len(day["hours"]) == 24
    for item in day["hours"]:
        assert item["expected_slots"] == 60
        counts[item["coverage"]] += 1
        if item["coverage"] == "zero_observation":
            assert item["observed_slots"] == 0
        if item["coverage"] == "complete":
            assert item["observed_slots"] == 60
    assert sum(counts.values()) == 24
    return counts


def _cli():
    path = Path(__file__).resolve().parents[2] / "scripts/research/reconcile_binance_usdm_klines.py"
    spec = importlib.util.spec_from_file_location("cex002_reconcile_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _retarget(root: Path, mutator) -> str:
    complete = root / ".complete"
    current = next(complete.iterdir())
    document = json.loads(current.read_text())
    mutator(document)
    body = sample.canonical_json(document)
    digest = sample.sha256_hex(body)
    current.unlink()
    (complete / f"{digest}.json").write_bytes(body)
    return digest


def test_pass_reports_zero_hours_without_filling_them(tmp_path: Path) -> None:
    world = assemble(tmp_path, [Day("0GUSDT", "2025-09-17", ("early",), header=False)])
    result, report = _run(world)
    assert result.status == "PASS"
    assert report["status"] == "PASS"
    assert report["full_history"] is False
    assert report["schema_version"] == 1
    assert report["document_type"] == rec.REPORT_DOCUMENT
    assert report["scope"] == rec.SCOPE
    account = report["accounting"]
    assert account["parsed_rows"] == 60
    assert account["compared_primary_rows"] == 60
    assert account["identical_duplicate_rows"] == 0
    assert account["uncomparable_rows"] == 0
    assert account["parsed_rows"] == (
        account["compared_primary_rows"] + account["identical_duplicate_rows"] + account["uncomparable_rows"]
    )
    coverage = report["coverage"]
    assert coverage["expected_hour_count"] == 24
    assert coverage["expected_slot_count"] == 1440
    assert coverage["observed_slot_count"] == 60
    assert coverage["zero_observation_hour_count"] == 23
    assert coverage["partial_hour_count"] == 0
    assert coverage["comparable_hour_count"] == 1
    assert coverage["uncomparable_hour_count"] == 23
    assert coverage["successfully_compared_hour_count"] == 1
    assert _counts(report["days"][0]) == {"complete": 1, "partial": 0, "zero_observation": 23}
    assert report["skipped_product_hours"] == []
    assert report["discrepancies"] == []
    zeros = [item for item in report["uncomparable_hours"] if item["coverage"] == "zero_observation"]
    assert len(zeros) == 23
    assert all(item["observed_slots"] == 0 and item["expected_slots"] == 60 for item in zeros)
    for product, width in ((BAR, 7), (FLOW, 9)):
        facts = coverage["per_product"][product]
        assert facts["skipped_hour_count"] == 0
        assert facts["successfully_compared_hour_count"] == 1
        assert len(facts["fields"]) == width
        assert all(item == {"denominator": 1, "matched": 1} for item in facts["fields"].values())
    identity = report["code_identity"]
    assert identity["acquisition_sha256"] == sample.sha256_hex(Path(sample.__file__).read_bytes())
    assert identity["reconciliation_sha256"] == sample.sha256_hex(Path(rec.__file__).read_bytes())
    cli_path = Path(rec.__file__).resolve().parents[3] / "scripts/research/reconcile_binance_usdm_klines.py"
    assert identity["cli_sha256"] == sample.sha256_hex(cli_path.read_bytes())
    report_bytes = result.report_path.read_bytes()
    assert RETRIEVAL.encode() not in report_bytes
    assert result.completion_sha256 is not None
    assert result.completion_sha256.encode() not in report_bytes
    replay, replay_report = _run(world)
    assert replay.report_reused is True
    assert replay.completion_reused is True
    assert replay.report_path.read_bytes() == report_bytes
    assert replay_report == report


def test_header_row_is_not_a_minute(tmp_path: Path) -> None:
    world = assemble(tmp_path, [Day("0GUSDT", "2025-09-17", ("early",), header=True)])
    result, report = _run(world)
    assert result.status == "PASS"
    assert report["accounting"]["parsed_rows"] == 60


@pytest.mark.parametrize("reason", ["within_object_missing_hour", "between_object_missing_hour"])
def test_skipped_product_hour_records_authenticated_gap_proof(tmp_path: Path, reason: str) -> None:
    day = Day(
        "0GUSDT",
        "2025-09-17",
        ("early",),
        hours=(Hour(flow=False),),
        gaps=(Gap(FLOW, 0, rec.MISSING_KIND, reason),),
    )
    world = assemble(tmp_path, [day])
    result, report = _run(world)
    assert result.status == "PASS"
    assert len(report["skipped_product_hours"]) == 1
    skip = report["skipped_product_hours"][0]
    hour = sample.utc_day_start_ms("2025-09-17")
    assert skip["product"] == FLOW
    assert skip["reason"] == reason
    assert skip["open_time"] == hour
    assert skip["close_time"] == hour + rec.HOUR_CLOSE
    proof = skip["gap_proof"]
    assert proof["exclusion_matched"] is False
    assert proof["quality_gap_parquet_sha256"] == world.proofs[FLOW]["parquet"]
    assert proof["quality_gap_lineage_sha256"] == world.proofs[FLOW]["lineage"]
    assert proof["provider_invalid_exclusions_sha256"] == world.proofs[FLOW]["exclusions"]
    flow = report["coverage"]["per_product"][FLOW]
    bar = report["coverage"]["per_product"][BAR]
    assert flow["skipped_hour_count"] == 1
    assert flow["successfully_compared_hour_count"] == 0
    assert all(item == {"denominator": 0, "matched": 0} for item in flow["fields"].values())
    assert bar["successfully_compared_hour_count"] == 1
    assert all(item == {"denominator": 1, "matched": 1} for item in bar["fields"].values())
    assert report["accounting"]["parsed_rows"] == 60


def test_provider_invalid_exclusion_is_recorded_and_a_missing_exclusion_is_not(tmp_path: Path) -> None:
    covered = Day(
        "0GUSDT",
        "2025-09-17",
        ("early",),
        hours=(Hour(bar=False),),
        gaps=(Gap(BAR, 0, rec.PROVIDER_KIND, rec.BAR_GAP_REASON, exclusion=True),),
    )
    world = assemble(tmp_path, [covered])
    _result, report = _run(world)
    assert report["status"] == "PASS"
    skip = report["skipped_product_hours"][0]
    assert skip["reason"] == rec.BAR_GAP_REASON
    assert skip["gap_proof"]["exclusion_matched"] is True
    assert skip["gap_proof"]["quality_gap_parquet_sha256"] == world.proofs[BAR]["parquet"]
    bare = tmp_path / "bare"
    missing = Day(
        "0GUSDT",
        "2025-09-17",
        ("early",),
        hours=(Hour(bar=False),),
        gaps=(Gap(BAR, 0, rec.PROVIDER_KIND, rec.BAR_GAP_REASON, exclusion=False),),
    )
    failed, failed_report = _run(assemble(bare, [missing]))
    assert failed.status == "FAILED"
    assert failed_report["skipped_product_hours"] == []
    assert failed_report["unexplained_absences"]
    _no_marker(bare / "output")


def test_wrong_reason_unknown_kind_and_overlap_stay_distinct(tmp_path: Path) -> None:
    wrong = assemble(
        tmp_path / "wrong",
        [Day("0GUSDT", "2025-09-17", ("early",), hours=(Hour(flow=False),), gaps=(Gap(FLOW, 0, rec.PROVIDER_KIND, rec.BAR_GAP_REASON),))],
    )
    wrong_result, wrong_report = _run(wrong)
    assert wrong_result.status == "FAILED"
    assert wrong_report["skipped_product_hours"] == []
    unknown = assemble(
        tmp_path / "unknown",
        [Day("0GUSDT", "2025-09-17", ("early",), hours=(Hour(flow=False),), gaps=(Gap(FLOW, 0, "not_a_real_kind", rec.MISSING_REASONS[0]),))],
    )
    _unknown_result, unknown_report = _run(unknown)
    assert unknown_report["status"] == "FAILED"
    assert unknown_report["skipped_product_hours"] == []
    overlap = assemble(
        tmp_path / "overlap",
        [Day("0GUSDT", "2025-09-17", ("early",), gaps=(Gap(BAR, 0, rec.MISSING_KIND, rec.MISSING_REASONS[0]),))],
    )
    _overlap_result, overlap_report = _run(overlap)
    assert overlap_report["status"] == "FAILED"
    assert overlap_report["skipped_product_hours"] == []
    assert any(item["kind"] == "accepted_row_overlaps_quality_gap" for item in overlap_report["discrepancies"])
    assert overlap_report["coverage"]["per_product"][BAR]["fields"]["open"]["denominator"] == 1


def test_both_products_explained_is_not_a_successful_comparison(tmp_path: Path) -> None:
    day = Day(
        "0GUSDT",
        "2025-09-17",
        ("early",),
        hours=(Hour(bar=False, flow=False),),
        gaps=(
            Gap(BAR, 0, rec.MISSING_KIND, rec.MISSING_REASONS[0]),
            Gap(FLOW, 0, rec.MISSING_KIND, rec.MISSING_REASONS[1]),
        ),
    )
    world = assemble(tmp_path, [day])
    result, report = _run(world)
    assert result.status == "FAILED"
    assert {item["product"] for item in report["skipped_product_hours"]} == {BAR, FLOW}
    assert report["coverage"]["successfully_compared_hour_count"] == 0
    assert any(item["kind"] == "day_without_compared_hour" for item in report["coverage_failures"])
    assert report["accounting"]["parsed_rows"] == 60
    for product in (BAR, FLOW):
        facts = report["coverage"]["per_product"][product]
        assert facts["skipped_hour_count"] == 1
        assert all(item["denominator"] == 0 for item in facts["fields"].values())
    _no_marker(world.output)


def test_partial_hour_beside_a_complete_hour_stays_pass(tmp_path: Path) -> None:
    day = Day(
        "0GUSDT",
        "2025-09-17",
        ("early",),
        hours=(Hour(index=0), Hour(index=1, count=59, bar=False, flow=False)),
    )
    _result, report = _run(assemble(tmp_path, [day]))
    assert report["status"] == "PASS"
    assert report["discrepancies"] == []
    assert report["accounting"]["parsed_rows"] == 119
    assert report["accounting"]["uncomparable_rows"] == 59
    assert report["coverage"]["observed_slot_count"] == 119
    assert report["coverage"]["partial_hour_count"] == 1
    assert report["coverage"]["zero_observation_hour_count"] == 22
    partial = [item for item in report["days"][0]["hours"] if item["coverage"] == "partial"]
    assert partial[0]["observed_slots"] == 59
    assert partial[0]["expected_slots"] == 60


def test_partial_only_day_is_coverage_failure_not_a_filled_hour(tmp_path: Path) -> None:
    day = Day("0GUSDT", "2025-09-17", ("early",), hours=(Hour(count=59, bar=False, flow=False),))
    world = assemble(tmp_path, [day])
    result, report = _run(world)
    assert result.status == "FAILED"
    assert report["discrepancies"] == []
    assert any(item["kind"] == "day_without_compared_hour" for item in report["coverage_failures"])
    assert _counts(report["days"][0])["partial"] == 1
    _no_marker(world.output)


def test_role_coverage_and_one_partial_day_fails_its_role(tmp_path: Path) -> None:
    days = [
        Day("0GUSDT", "2025-09-17", ("early",)),
        Day("0GUSDT", "2026-03-21", ("middle",)),
        Day("1000BTTCUSDT", "2022-04-11", ("recent", "delisted")),
    ]
    _result, report = _run(assemble(tmp_path / "roles", days))
    assert report["status"] == "PASS"
    assert report["coverage"]["roles_with_compared_hour"] == 4
    assert report["coverage"]["distinct_day_count"] == 3
    mixed = [
        Day("0GUSDT", "2025-09-17", ("early",)),
        Day("KAIAUSDT", "2024-12-04", ("recent",), hours=(Hour(count=59, bar=False, flow=False),)),
    ]
    failed, failed_report = _run(assemble(tmp_path / "mixed", mixed))
    assert failed.status == "FAILED"
    assert any(
        item["kind"] == "day_without_compared_hour" and item["utc_date"] == "2024-12-04"
        for item in failed_report["coverage_failures"]
    )


def test_exact_decimal_ignores_ambient_precision(tmp_path: Path) -> None:
    day = Day("0GUSDT", "2025-09-17", ("early",), hours=(Hour(tokens={"volume": "1.000001"}),))
    world = assemble(tmp_path, [day])
    with localcontext() as context:
        context.prec = 6
        result, report = _run(world)
    assert result.status == "PASS"
    assert report["coverage"]["per_product"][BAR]["fields"]["volume"] == {"denominator": 1, "matched": 1}


def test_shuffled_minutes_and_identical_duplicate(tmp_path: Path) -> None:
    start = sample.utc_day_start_ms("2025-09-17")
    rows = []
    for index in range(60):
        tokens = {"high": "110", "low": "90"}
        if index == 0:
            tokens["open"] = "90"
        if index == 59:
            tokens["close"] = "110"
        rows.append(_minute(start + index * rec.MINUTE_MS, tokens))
    rows.reverse()
    shuffled = assemble(tmp_path / "shuffled", [Day("0GUSDT", "2025-09-17", ("early",), hours=(Hour(rows=rows),))])
    assert _run(shuffled)[0].status == "PASS"
    duplicated = assemble(
        tmp_path / "duplicate",
        [Day("0GUSDT", "2025-09-17", ("early",), hours=(Hour(duplicate_first=True),))],
    )
    _result, report = _run(duplicated)
    assert report["status"] == "PASS"
    assert report["accounting"]["parsed_rows"] == 61
    assert report["accounting"]["identical_duplicate_rows"] == 1
    assert report["accounting"]["compared_primary_rows"] == 60
    assert report["coverage"]["observed_slot_count"] == 60


def test_two_hours_match_by_open_time_when_parquet_order_is_reversed(tmp_path: Path) -> None:
    day = Day("0GUSDT", "2025-09-17", ("early",), hours=(Hour(index=0), Hour(index=1)))
    _result, report = _run(assemble(tmp_path, [day], reverse_products=True))
    assert report["status"] == "PASS"
    assert report["coverage"]["comparable_hour_count"] == 2
    assert report["coverage"]["zero_observation_hour_count"] == 22
    assert report["coverage"]["successfully_compared_hour_count"] == 2


def test_zero_imbalance_matches(tmp_path: Path) -> None:
    tokens = {"volume": "1", "taker_buy_volume": "0.5", "quote_volume": "100", "taker_buy_quote_volume": "50"}
    world = assemble(tmp_path, [Day("0GUSDT", "2025-09-17", ("early",), hours=(Hour(tokens=tokens),))])
    _result, report = _run(world)
    assert report["status"] == "PASS"
    assert report["coverage"]["per_product"][FLOW]["fields"]["volume_imbalance"] == {"denominator": 1, "matched": 1}


@pytest.mark.parametrize(("product", "name"), FIELD_CASES)
def test_each_compared_field_mismatch_fails_without_completion(tmp_path: Path, product: str, name: str) -> None:
    start = sample.utc_day_start_ms("2025-09-17")
    rows = [_minute(start + index * rec.MINUTE_MS) for index in range(60)]
    base = _aggregate(rows)
    if name == "trade_count":
        updated = 61
    elif name == "volume_imbalance":
        updated = 0
    else:
        updated = base[name] + 1
    override = {name: updated}
    hour = Hour(
        rows=rows,
        bar_override=override if product == BAR else None,
        flow_override=override if product == FLOW else None,
    )
    world = assemble(tmp_path, [Day("0GUSDT", "2025-09-17", ("early",), hours=(hour,))])
    result, report = _run(world)
    assert result.status == "FAILED"
    found = [item for item in report["discrepancies"] if item["kind"] == "field_mismatch" and item["field"] == name]
    assert len(found) == 1
    assert found[0]["product"] == product
    if name in rec.DERIVED_FIELDS:
        assert found[0]["source_tokens"] is None
        assert found[0]["derived_inputs"]
    else:
        assert found[0]["source_tokens"]
    _no_marker(world.output)


def test_close_time_mismatch_is_not_an_unexplained_absence(tmp_path: Path) -> None:
    hour = Hour(bar_close_delta=1)
    world = assemble(tmp_path, [Day("0GUSDT", "2025-09-17", ("early",), hours=(hour,))])
    result, report = _run(world)
    assert result.status == "FAILED"
    assert any(item["kind"] == "close_time_mismatch" for item in report["discrepancies"])
    assert report["unexplained_absences"] == []
    _no_marker(world.output)


def test_structural_minute_failures_raise_and_gaps_do_not_hide_them(tmp_path: Path) -> None:
    start = sample.utc_day_start_ms("2025-09-17")
    gap = (Gap(BAR, 0, rec.MISSING_KIND, rec.MISSING_REASONS[0]),)

    def raise_for(rows: list[list[str]], message: str) -> None:
        folder = tmp_path / "_".join(message.split())
        day = Day("0GUSDT", "2025-09-17", ("early",), hours=(Hour(rows=rows, bar=False, flow=False),), gaps=gap)
        world = assemble(folder, [day])
        with pytest.raises(rec.ReconciliationError, match=message):
            rec.reconcile(world.policy, world.evidence, world.output)
        _no_marker(world.output)

    raise_for([_minute(start // 1000)], "minute open_time is not a UTC minute")
    outside = _minute(start + rec.DAY_MS)
    raise_for([outside], "minute row is outside its UTC day")
    misaligned = _minute(start)
    misaligned[6] = str(start + 60_000)
    raise_for([misaligned], "minute close_time is not aligned")
    low = _minute(start, {"volume": "-1"})
    raise_for([low], "minute value is negative")
    taker = [
        _minute(start + index * rec.MINUTE_MS, {"taker_buy_volume": "2"})
        for index in range(60)
    ]
    raise_for(taker, "taker volume exceeds its total")
    first = _minute(start)
    second = _minute(start, {"volume": "1.0"})
    raise_for([first, second], "conflicting minute tokens")


def test_cross_month_gap_duplicate_open_and_foreign_close_raise(tmp_path: Path) -> None:
    begin = sample.utc_day_start_ms("2025-09-30") + 23 * rec.HOUR_MS
    end = sample.utc_day_start_ms("2025-10-01")
    crossed = Day(
        "0GUSDT",
        "2025-09-17",
        ("early",),
        gaps=(Gap(BAR, 0, rec.MISSING_KIND, rec.MISSING_REASONS[0], start_ms=begin, end_ms=end),),
    )
    world = assemble(tmp_path / "cross", [crossed])
    with pytest.raises(rec.ReconciliationError, match="quality gap row crosses a UTC month"):
        rec.reconcile(world.policy, world.evidence, world.output)
    _no_marker(world.output)
    duplicated = assemble(tmp_path / "dup", [Day("0GUSDT", "2025-09-17", ("early",), duplicate_open=True)])
    with pytest.raises(rec.ReconciliationError, match="duplicate product open_time"):
        rec.reconcile(duplicated.policy, duplicated.evidence, duplicated.output)
    foreign = assemble(tmp_path / "foreign", [Day("0GUSDT", "2025-09-17", ("early",), bad_foreign=True)])
    with pytest.raises(rec.ReconciliationError, match="partition row close_time is invalid"):
        rec.reconcile(foreign.policy, foreign.evidence, foreign.output)


def test_product_completion_authentication_failures(tmp_path: Path) -> None:
    missing = assemble(tmp_path / "missing", [Day("0GUSDT", "2025-09-17", ("early",))])
    next((missing.roots[BAR] / ".complete").iterdir()).unlink()
    with pytest.raises(rec.ReconciliationError, match="product completion is missing"):
        rec.reconcile(missing.policy, missing.evidence, missing.output)

    renamed = assemble(tmp_path / "renamed", [Day("0GUSDT", "2025-09-17", ("early",))])
    current = next((renamed.roots[BAR] / ".complete").iterdir())
    current.rename(current.parent / "not-the-hash.json")
    with pytest.raises(rec.ReconciliationError, match="product completion name does not match its bytes"):
        rec.reconcile(renamed.policy, renamed.evidence, renamed.output)

    digest = assemble(tmp_path / "digest", [Day("0GUSDT", "2025-09-17", ("early",))])
    policy = replace(digest.policy, bar_completion="cd" * 32)
    with pytest.raises(rec.ReconciliationError, match="product completion digest mismatch"):
        rec.reconcile(policy, digest.evidence, digest.output)

    schema = assemble(tmp_path / "schema", [Day("0GUSDT", "2025-09-17", ("early",))])
    updated = _retarget(schema.roots[BAR], lambda document: document.__setitem__("schema_sha256", "ab" * 32))
    with pytest.raises(rec.ReconciliationError, match="product schema identity mismatch"):
        rec.reconcile(replace(schema.policy, bar_completion=updated), schema.evidence, schema.output)

    lineage = assemble(tmp_path / "lineage", [Day("0GUSDT", "2025-09-17", ("early",))])
    lineage_path = next((lineage.roots[BAR]).glob(".lineage/**/*.json"))
    payload = bytearray(lineage_path.read_bytes())
    payload[-2] ^= 0x01
    lineage_path.write_bytes(payload)
    with pytest.raises(rec.ReconciliationError, match="partition lineage mismatch"):
        rec.reconcile(lineage.policy, lineage.evidence, lineage.output)

    parquet = assemble(tmp_path / "parquet", [Day("0GUSDT", "2025-09-17", ("early",))])
    parquet_path = next(parquet.roots[BAR].glob(".partitions/**/*.parquet"))
    raw = bytearray(parquet_path.read_bytes())
    raw[-2] ^= 0x01
    parquet_path.write_bytes(raw)
    with pytest.raises(rec.ReconciliationError, match="partition parquet digest mismatch"):
        rec.reconcile(parquet.policy, parquet.evidence, parquet.output)

    absent = assemble(tmp_path / "absent", [Day("0GUSDT", "2025-09-17", ("early",))])
    pinned = _retarget(absent.roots[BAR], lambda document: document.__setitem__("partitions", []))
    with pytest.raises(rec.ReconciliationError, match="selected partition is missing"):
        rec.reconcile(replace(absent.policy, bar_completion=pinned), absent.evidence, absent.output)


def test_output_isolation(tmp_path: Path) -> None:
    world = assemble(tmp_path, [Day("0GUSDT", "2025-09-17", ("early",))])
    with pytest.raises(sample.SampleError, match="evidence and comparison output overlap"):
        rec.reconcile(world.policy, world.evidence, world.evidence)
    with pytest.raises(sample.SampleError, match="sample output overlaps a protected root"):
        rec.reconcile(world.policy, world.evidence, world.repo / "products" / "bar" / "nested")
    target = tmp_path / "real-output"
    target.mkdir()
    link = tmp_path / "linked-output"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(sample.SampleError, match="path contains a symlink"):
        rec.reconcile(world.policy, world.evidence, link)


def test_failed_replay_and_conflicting_completion_marker(tmp_path: Path) -> None:
    hour = Hour(bar_override={"trade_count": 61})
    world = assemble(tmp_path / "failed", [Day("0GUSDT", "2025-09-17", ("early",), hours=(hour,))])
    first, first_report = _run(world)
    assert first.status == "FAILED"
    assert first_report["status"] == "FAILED"
    _no_marker(world.output)
    second, second_report = _run(world)
    assert second.report_reused is True
    assert second.completion_sha256 is None
    assert second_report == first_report

    planted_fail = assemble(tmp_path / "plant-fail", [Day("0GUSDT", "2025-09-17", ("early",), hours=(hour,))])
    marker = planted_fail.output / ".complete"
    marker.mkdir(parents=True)
    bogus = marker / "bogus.json"
    bogus.write_bytes(b"PLANTED")
    with pytest.raises(rec.ReconciliationError, match="conflicting reconciliation completion"):
        rec.reconcile(planted_fail.policy, planted_fail.evidence, planted_fail.output)
    assert bogus.read_bytes() == b"PLANTED"

    planted_pass = assemble(tmp_path / "plant-pass", [Day("0GUSDT", "2025-09-17", ("early",))])
    pass_marker = planted_pass.output / ".complete"
    pass_marker.mkdir(parents=True)
    pass_bogus = pass_marker / "bogus.json"
    pass_bogus.write_bytes(b"PLANTED")
    with pytest.raises(rec.ReconciliationError, match="conflicting reconciliation completion"):
        rec.reconcile(planted_pass.policy, planted_pass.evidence, planted_pass.output)
    assert pass_bogus.read_bytes() == b"PLANTED"


def test_cli_usage_pass_and_missing_sample(tmp_path: Path) -> None:
    command = _cli()
    assert command.main(["--symbol", "BTCUSDT"]) == 2
    assert command.main(["--evidence-root", "e", "--output-root", "o", "--schema", "x"]) == 2
    assert command.main(["--evidence-root", "e", "--output-root", "o", "--report-sha", "ab"]) == 2
    assert command.main(["--repo", "."]) == 2
    world = assemble(tmp_path, [Day("0GUSDT", "2025-09-17", ("early",))])

    class Exploding:
        def __init__(self) -> None:
            self.calls = 0

        def fetch(self, url: str, *, timeout: float, max_bytes: int):
            self.calls += 1
            raise AssertionError(url)

    exploding = Exploding()
    code = command.main(
        ["--repo", str(world.repo), "--evidence-root", str(world.evidence), "--output-root", str(world.output)],
        policy=world.policy,
        transport=exploding,
    )
    assert code == 0
    assert exploding.calls == 0
    again = Exploding()
    fetched = command.main(
        [
            "--repo",
            str(world.repo),
            "--evidence-root",
            str(world.evidence),
            "--output-root",
            str(world.output),
            "--fetch",
        ],
        policy=world.policy,
        transport=again,
    )
    assert fetched == 0
    assert again.calls == 0
    absent = Exploding()
    missing = command.main(
        [
            "--repo",
            str(world.repo),
            "--evidence-root",
            str(tmp_path / "absent-evidence"),
            "--output-root",
            str(tmp_path / "absent-output"),
        ],
        policy=world.policy,
        transport=absent,
    )
    assert missing == 1
    assert absent.calls == 0
    mismatch = assemble(
        tmp_path / "cli-fail",
        [Day("0GUSDT", "2025-09-17", ("early",), hours=(Hour(bar_override={"trade_count": 61}),))],
    )
    assert command.main(
        ["--repo", str(mismatch.repo), "--evidence-root", str(mismatch.evidence), "--output-root", str(mismatch.output)],
        policy=mismatch.policy,
    ) == 1
    _no_marker(mismatch.output)
