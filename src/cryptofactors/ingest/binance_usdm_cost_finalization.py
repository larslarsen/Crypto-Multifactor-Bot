"""Finalize the exact reviewed, preserved Binance USD-M cost product.

This module never decodes a source ZIP and never writes Parquet.  It authenticates
the frozen authorities and raw compressed objects, independently validates the
already encoded product in bounded Arrow batches, and publishes only completion.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

import cryptofactors.ingest.binance_usdm_cost_calibration as producer
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    COST_COMPONENTS,
    FEE_AUTHORITY_CLASS,
    FEE_GAP_KIND,
    FEE_POLICY_KNOWN_AT,
    SIZING_ROW_BATCH,
    fee_scenario_rows,
    writer_identity,
)

Error = producer.CostCalibrationError

ORIGINAL_PRODUCER_SHA256 = "2026982aa275ffb09e5dceb75453d0290cd7c0b35e248f48e45cf3f3cee3b41d"
ORIGINAL_INTEGRATION_COMMIT = "e092d17afa3d229135d89fa144ddc2b120e8e2f7"
PRESERVED_INVENTORY_SHA256 = "482cda93ba68c93d46a17207bbb6b01764dd5b66d72d936860eba67d2f399b98"
PRESERVED_FILES = 7_731
PRESERVED_DIRECTORIES = 11_386
PRESERVED_BYTES = 17_940_823_719
SOURCE_ROW_FACTS_SHA256 = "aac31786a8f18088481cd00579c30dece80cf9907c792638d2e0047c076fc89b"
SOURCE_GAP_SHA256 = "aace941a43e38c2f790fed4c383e08cbbd27d3f5f7215bc95b50bb134ae3519e"
SOURCE_GAP_BYTES = 178_783

EXPECTED_SOURCE_OBJECTS = 3_144
EXPECTED_SOURCE_BYTES = 12_522_974_218
EXPECTED_GENERATION0_OBJECTS = 2_790
EXPECTED_RECOVERY_OBJECTS = 354
EXPECTED_TICKER_OBJECTS = 909
EXPECTED_DEPTH_OBJECTS = 2_235
EXPECTED_MEMBERSHIPS = 771
EXPECTED_SOURCE_GAPS = 494
EXPECTED_BOOK_ROWS = 939_130_319
EXPECTED_ALL_ROWS = 939_131_092
EXPECTED_QUOTE_STATES: Mapping[str, int] = {
    "two_sided": 882_075_718,
    "bid_only": 279,
    "ask_only": 76,
    "empty": 17,
}
EXPECTED_COMPONENTS: Mapping[str, Mapping[str, int]] = {
    producer.COMPONENT_TICKER: {
        "partitions": 866,
        "rows": 882_076_090,
        "parquet_bytes": 16_475_583_828,
        "largest_partition_bytes": 368_974_047,
    },
    producer.COMPONENT_DEPTH: {
        "partitions": 2_226,
        "rows": 57_054_229,
        "parquet_bytes": 1_455_739_653,
        "largest_partition_bytes": 1_977_525,
    },
    producer.COMPONENT_FEE_GAP: {
        "partitions": 771,
        "rows": 771,
        "parquet_bytes": 2_634_470,
        "largest_partition_bytes": 3_428,
    },
    producer.COMPONENT_OFFICIAL_FEE: {
        "partitions": 1,
        "rows": 0,
        "parquet_bytes": 3_551,
        "largest_partition_bytes": 3_551,
    },
    producer.COMPONENT_SCENARIO: {
        "partitions": 1,
        "rows": 2,
        "parquet_bytes": 3_651,
        "largest_partition_bytes": 3_651,
    },
}


@dataclass(frozen=True, slots=True)
class FinalizationHooks:
    before_completion_publish: Callable[[Path, Path], None] | None = None


@dataclass(frozen=True, slots=True)
class CostFinalizationResult:
    completion_path: Path
    completion_sha256: str
    completion_reused: bool
    partition_count: int
    source_rows: int


@dataclass(frozen=True, slots=True)
class _Inventory:
    entries: tuple[Mapping[str, Any], ...]
    files: frozenset[str]
    directories: frozenset[str]
    completion: str | None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Error(message)


def _canonical_json(value: Any, *, newline: bool) -> bytes:
    suffix = "\n" if newline else ""
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + suffix).encode()


def _producer_path() -> Path:
    path = Path(producer.__file__ or "")
    _require(path.is_file(), "accepted producer module is unavailable")
    return path


def _verify_producer() -> None:
    _require(
        hashlib.sha256(_producer_path().read_bytes()).hexdigest()
        == ORIGINAL_PRODUCER_SHA256,
        "accepted producer module identity changed",
    )


def _read_json(tree: producer._OutputTree, relative: str, digest: str, size: int) -> Mapping[str, Any]:
    path = tree.root.joinpath(*PurePosixPath(relative).parts)
    return producer._reprove_json(tree, path, digest, size)


def _file_entry(tree: producer._OutputTree, relative: str) -> Mapping[str, Any]:
    fd = tree.open_final(tree.root.joinpath(*PurePosixPath(relative).parts))
    try:
        digest, size = producer._hash_fd(fd)
    finally:
        os.close(fd)
    suffix = PurePosixPath(relative).suffix
    _require(suffix in {".json", ".parquet"}, "preserved inventory contains an unexpected file type")
    _require(PurePosixPath(relative).stem == digest, "preserved artifact content address changed")
    return {"path": relative, "sha256": digest, "bytes": size}


def _expected_directories(files: set[str], *, completion: bool) -> set[str]:
    result = {".staging"}
    for relative in files:
        parts = PurePosixPath(relative).parts[:-1]
        for length in range(1, len(parts) + 1):
            result.add("/".join(parts[:length]))
    if completion:
        result.add(".complete")
    return result


def _inventory(tree: producer._OutputTree) -> _Inventory:
    files, directories = tree.inventory()
    completion_names = sorted(
        value for value in files if PurePosixPath(value).parts[:1] == (".complete",)
    )
    _require(len(completion_names) <= 1, "completion inventory is conflicting")
    completion = completion_names[0] if completion_names else None
    preserved = files - set(completion_names)
    _require(len(preserved) == PRESERVED_FILES, "preserved file inventory count changed")
    entries = tuple(_file_entry(tree, relative) for relative in sorted(preserved))
    digest = hashlib.sha256(_canonical_json(entries, newline=False)).hexdigest()
    _require(digest == PRESERVED_INVENTORY_SHA256, "preserved inventory identity changed")
    _require(sum(int(item["bytes"]) for item in entries) == PRESERVED_BYTES, "preserved inventory byte total changed")
    has_completion_directory = ".complete" in directories
    expected_directories = _expected_directories(files, completion=has_completion_directory)
    _require(directories == expected_directories, "preserved directory inventory changed")
    expected_count = PRESERVED_DIRECTORIES + (1 if has_completion_directory else 0)
    _require(len(directories) == expected_count, "preserved directory count changed")
    return _Inventory(entries, frozenset(files), frozenset(directories), completion)


def _authenticate_sources(sources: Sequence[producer.RawCostObject]) -> None:
    for source in sources:
        fd = producer._open_authenticated(
            source.path,
            source.source_sha256,
            source.byte_size,
            producer.MAX_COMPRESSED_OBJECT_BYTES,
        )
        os.close(fd)


def _source_equation(sources: Sequence[producer.RawCostObject]) -> None:
    counts = Counter(source.family for source in sources)
    authorities = Counter(source.authority for source in sources)
    _require(len(sources) == EXPECTED_SOURCE_OBJECTS, "authenticated source count changed")
    _require(sum(source.byte_size for source in sources) == EXPECTED_SOURCE_BYTES, "authenticated source bytes changed")
    _require(
        counts
        == Counter(
            {
                producer.FAMILY_TICKER: EXPECTED_TICKER_OBJECTS,
                producer.FAMILY_DEPTH: EXPECTED_DEPTH_OBJECTS,
            }
        ),
        "authenticated source family equation changed",
    )
    _require(
        authorities
        == Counter(
            {
                "accepted_generation_0_completion": EXPECTED_GENERATION0_OBJECTS,
                "accepted_v3_direct_recovery": EXPECTED_RECOVERY_OBJECTS,
            }
        ),
        "authenticated source authority equation changed",
    )


def _parse_lineages(
    tree: producer._OutputTree,
    inventory: _Inventory,
    sources: Sequence[producer.RawCostObject],
) -> tuple[tuple[producer.PublishedComponent, ...], Mapping[str, tuple[Mapping[str, Any], ...]]]:
    entries = {str(item["path"]): item for item in inventory.entries}
    source_by_key = {source.source_key: source for source in sources}
    components: list[producer.PublishedComponent] = []
    raw_objects_by_lineage: dict[str, tuple[Mapping[str, Any], ...]] = {}
    lineage_paths = sorted(path for path in entries if path.startswith(".lineage/"))
    _require(len(lineage_paths) == sum(value["partitions"] for value in EXPECTED_COMPONENTS.values()), "lineage count changed")
    for relative in lineage_paths:
        entry = entries[relative]
        document = _read_json(tree, relative, str(entry["sha256"]), int(entry["bytes"]))
        parts = PurePosixPath(relative).parts
        _require(len(parts) == 5, "lineage path shape changed")
        _prefix, component, symbol, month, _name = parts
        _require(component in EXPECTED_COMPONENTS, "lineage component changed")
        parquet_relative = str(document.get("parquet_path") or "")
        parquet_entry = entries.get(parquet_relative)
        _require(parquet_entry is not None, "lineage names a missing Parquet artifact")
        _require(
            PurePosixPath(parquet_relative).parts[:4]
            == (".partitions", component, symbol, month),
            "lineage Parquet ownership changed",
        )
        _require(
            document.get("component") == component
            and document.get("row_count") is not None
            and document.get("schema_sha256") == producer.SCHEMA_IDENTITIES[component]
            and document.get("parquet_sha256") == parquet_entry["sha256"]
            and document.get("parquet_bytes") == parquet_entry["bytes"],
            "lineage descriptor changed",
        )
        row_count = document["row_count"]
        _require(type(row_count) is int and row_count >= 0, "lineage row count changed")
        raw_objects: tuple[Mapping[str, Any], ...] = ()
        ranges: tuple[Mapping[str, Any], ...] = ()
        if component in {producer.COMPONENT_TICKER, producer.COMPONENT_DEPTH}:
            _require(
                document.get("document_type") == f"{producer.PRODUCT}_{component}_partition_lineage"
                and document.get("native_symbol") == symbol
                and document.get("utc_month") == month
                and document.get("writer_identity") == writer_identity()
                and document.get("partition_time_basis")
                == ("transaction_time" if component == producer.COMPONENT_TICKER else "source_timestamp"),
                "book lineage facts changed",
            )
            raw_value = document.get("raw_objects")
            range_value = document.get("source_ordinal_ranges")
            _require(type(raw_value) is list and type(range_value) is list, "book lineage mappings changed")
            _require(
                all(type(value) is dict for value in raw_value)
                and all(type(value) is dict for value in range_value),
                "book lineage mappings changed",
            )
            raw_objects = tuple(raw_value)
            ranges = tuple(range_value)
            for index, fact in enumerate(raw_objects):
                _require(type(fact) is dict and fact.get("raw_object_ref") == index, "lineage raw reference changed")
                key = fact.get("source_key")
                source = source_by_key.get(key)
                expected_family = (
                    producer.FAMILY_TICKER
                    if component == producer.COMPONENT_TICKER
                    else producer.FAMILY_DEPTH
                )
                _require(
                    source is not None
                    and source.family == expected_family
                    and fact == producer._source_lineage(source, index),
                    "lineage source authority changed",
                )
            raw_objects_by_lineage[relative] = raw_objects
        elif component == producer.COMPONENT_OFFICIAL_FEE:
            _require(
                symbol == "__schema__"
                and month == "schema"
                and document.get("document_type") == f"{producer.PRODUCT}_{component}_lineage"
                and document.get("required_product") == producer.PRODUCT
                and document.get("authority_state") == "historical_fee_schedule_unavailable",
                "official fee lineage changed",
            )
        elif component == producer.COMPONENT_FEE_GAP:
            _require(
                month == "authority"
                and document.get("document_type") == f"{producer.PRODUCT}_{component}_lineage"
                and document.get("required_product") == producer.PRODUCT
                and document.get("native_symbol") == symbol
                and document.get("membership_completion_sha256") == producer.MEMBERSHIP_COMPLETION_SHA256,
                "fee gap lineage changed",
            )
        else:
            _require(
                symbol == "BINANCE_USDM"
                and month == "configuration"
                and document.get("document_type") == f"{producer.PRODUCT}_{component}_lineage"
                and document.get("required_product") == producer.PRODUCT
                and document.get("policy_known_at") == FEE_POLICY_KNOWN_AT
                and document.get("historical_observation") is False,
                "scenario lineage changed",
            )
        components.append(
            producer.PublishedComponent(
                component,
                symbol,
                month,
                row_count,
                tree.root.joinpath(*PurePosixPath(parquet_relative).parts),
                str(parquet_entry["sha256"]),
                int(parquet_entry["bytes"]),
                tree.root.joinpath(*parts),
                str(entry["sha256"]),
                int(entry["bytes"]),
                ranges,
                True,
            )
        )
    parquet_paths = {str(item.parquet_path.relative_to(tree.root)) for item in components}
    _require(
        parquet_paths == {path for path in entries if path.startswith(".partitions/")},
        "Parquet inventory is not exactly lineage-described",
    )
    return tuple(components), raw_objects_by_lineage


def _identity_values(identity: producer.MembershipIdentity) -> Mapping[str, Any]:
    return {"venue_symbol": identity.native_symbol, **identity.row()}


def _column(batch: pa.RecordBatch, name: str) -> pa.Array:
    return batch.column(batch.schema.get_field_index(name))


def _all(value: pa.Array | pa.ChunkedArray) -> bool:
    reduced = pc.all(value)
    return reduced.is_valid and reduced.as_py() is True


def _validate_identity(batch: pa.RecordBatch, expected: Mapping[str, Any]) -> None:
    for name, value in expected.items():
        column = _column(batch, name)
        if value is None:
            _require(column.null_count == len(column), "encoded null membership identity changed")
        else:
            comparable = pc.cast(column, column.type.value_type) if pa.types.is_dictionary(column.type) else column
            _require(
                column.null_count == 0
                and _all(pc.equal(comparable, pa.scalar(value, type=comparable.type))),
                "encoded membership identity changed",
            )


def _scan_book(
    parquet: pq.ParquetFile,
    item: producer.PublishedComponent,
    lineage_raw: tuple[Mapping[str, Any], ...],
    identity: producer.MembershipIdentity,
) -> tuple[Counter[str], Mapping[str, tuple[int, int, int]]]:
    ranges = {int(value["raw_object_ref"]): value for value in item.source_ordinal_ranges}
    _require(len(ranges) == len(item.source_ordinal_ranges), "lineage ordinal references repeat")
    _require(
        all(
            type(value.get("raw_object_ref")) is int
            and 0 <= value["raw_object_ref"] < len(lineage_raw)
            and type(value.get("source_key")) is str
            and value["source_key"] == lineage_raw[value["raw_object_ref"]]["source_key"]
            and all(type(value.get(name)) is int for name in ("first", "last", "retained_rows", "physical_rows"))
            for value in item.source_ordinal_ranges
        ),
        "lineage ordinal reference changed",
    )
    cursors = {ref: int(value["first"]) for ref, value in ranges.items()}
    seen = Counter()
    states: Counter[str] = Counter()
    previous: dict[int, int] = {}
    expected_identity = _identity_values(identity)
    for batch in parquet.iter_batches(batch_size=SIZING_ROW_BATCH):
        _require(batch.num_rows <= SIZING_ROW_BATCH, "Parquet batch bound changed")
        _validate_identity(batch, expected_identity)
        raw_ref_column = _column(batch, "raw_object_ref")
        ordinal_column = _column(batch, "source_row_ordinal")
        moment_column = _column(
            batch,
            "transaction_time" if item.component == producer.COMPONENT_TICKER else "timestamp",
        )
        _require(
            raw_ref_column.null_count == ordinal_column.null_count == moment_column.null_count == 0,
            "encoded reference or time column contains null",
        )
        raw_refs = raw_ref_column.to_numpy(zero_copy_only=False)
        ordinals = ordinal_column.to_numpy(zero_copy_only=False)
        _require(raw_refs.size == batch.num_rows and ordinals.size == batch.num_rows, "encoded reference columns changed")
        boundaries = np.concatenate((np.array([0]), np.flatnonzero(np.diff(raw_refs) != 0) + 1, np.array([batch.num_rows])))
        moments = moment_column.to_numpy(zero_copy_only=False)
        try:
            month_start = int(datetime.strptime(item.utc_month, "%Y-%m").replace(tzinfo=UTC).timestamp() * 1000)
        except ValueError as exc:
            raise Error("encoded partition month is invalid") from exc
        if item.utc_month.endswith("-12"):
            next_month = f"{int(item.utc_month[:4]) + 1:04d}-01"
        else:
            next_month = f"{item.utc_month[:5]}{int(item.utc_month[5:]) + 1:02d}"
        month_end = int(datetime.strptime(next_month, "%Y-%m").replace(tzinfo=UTC).timestamp() * 1000)
        _require(bool(np.all((moments >= month_start) & (moments < month_end))), "encoded row month ownership changed")
        for start, stop in zip(boundaries[:-1], boundaries[1:], strict=True):
            raw_ref = int(raw_refs[start])
            _require(raw_ref in ranges and bool(np.all(raw_refs[start:stop] == raw_ref)), "encoded raw reference changed")
            run = ordinals[start:stop]
            _require(int(run[0]) == cursors[raw_ref] and (len(run) == 1 or bool(np.all(np.diff(run) == 1))), "encoded source ordinal changed")
            cursors[raw_ref] += len(run)
            seen[raw_ref] += len(run)
            source = lineage_raw[raw_ref]
            _require(source["source_key"].split("/")[-2] == identity.native_symbol, "encoded source symbol changed")
            day_start = producer._day_start_ms(str(source["economic_day"]))
            run_moments = moments[start:stop]
            _require(bool(np.all((run_moments >= day_start) & (run_moments <= day_start + 86_400_000))), "encoded row source-day ownership changed")
            _require(int(run_moments[0]) >= previous.get(raw_ref, 0) and (len(run_moments) == 1 or bool(np.all(np.diff(run_moments) >= 0))), "encoded source time moves backwards")
            previous[raw_ref] = int(run_moments[-1])
        if item.component == producer.COMPONENT_TICKER:
            update = _column(batch, "update_id")
            transaction = _column(batch, "transaction_time")
            event = _column(batch, "event_time")
            _require(update.null_count == transaction.null_count == event.null_count == 0 and _all(pc.greater_equal(update, 0)) and _all(pc.greater(transaction, 0)) and _all(pc.greater(event, 0)), "encoded ticker integer domain changed")
            bid = _column(batch, "best_bid_price")
            bid_qty = _column(batch, "best_bid_qty")
            ask = _column(batch, "best_ask_price")
            ask_qty = _column(batch, "best_ask_qty")
            quote_columns = (bid, bid_qty, ask, ask_qty)
            quote_zeros = tuple(pa.scalar(Decimal(0), type=value.type) for value in quote_columns)
            _require(
                all(
                    value.null_count == 0 and _all(pc.greater_equal(value, zero))
                    for value, zero in zip(quote_columns, quote_zeros, strict=True)
                ),
                "encoded ticker quote domain changed",
            )
            bid_positive = pc.greater(bid, quote_zeros[0])
            ask_positive = pc.greater(ask, quote_zeros[2])
            _require(_all(pc.invert(pc.and_(pc.invert(bid_positive), pc.greater(bid_qty, quote_zeros[1])))) and _all(pc.invert(pc.and_(pc.invert(ask_positive), pc.greater(ask_qty, quote_zeros[3])))), "encoded ticker zero-state changed")
            _require(_all(pc.invert(pc.and_(pc.and_(bid_positive, ask_positive), pc.greater(bid, ask)))), "encoded ticker quote is crossed")
            states["two_sided"] += int(pc.sum(pc.and_(bid_positive, ask_positive)).as_py())
            states["bid_only"] += int(pc.sum(pc.and_(bid_positive, pc.invert(ask_positive))).as_py())
            states["ask_only"] += int(pc.sum(pc.and_(pc.invert(bid_positive), ask_positive)).as_py())
            states["empty"] += int(pc.sum(pc.and_(pc.invert(bid_positive), pc.invert(ask_positive))).as_py())
        else:
            percentage = _column(batch, "percentage")
            depth = _column(batch, "depth")
            notional = _column(batch, "notional")
            percentage_zero = pa.scalar(Decimal(0), type=percentage.type)
            depth_zero = pa.scalar(Decimal(0), type=depth.type)
            notional_zero = pa.scalar(Decimal(0), type=notional.type)
            _require(percentage.null_count == depth.null_count == notional.null_count == 0 and _all(pc.not_equal(percentage, percentage_zero)), "encoded depth time or band changed")
            _require(_all(pc.greater_equal(depth, depth_zero)) and _all(pc.greater_equal(notional, notional_zero)), "encoded depth value changed")
    facts: dict[str, tuple[int, int, int]] = {}
    for raw_ref, value in ranges.items():
        first = int(value["first"])
        last = int(value["last"])
        physical = int(value["physical_rows"])
        retained = int(value["retained_rows"])
        _require(0 <= first <= last < physical and retained == last - first + 1, "lineage ordinal domain changed")
        _require(seen[raw_ref] == retained and cursors[raw_ref] == last + 1, "encoded ordinal range is incomplete")
        facts[str(value["source_key"])] = (first, last, physical)
    _require(sum(seen.values()) == item.row_count, "encoded partition row count changed")
    return states, facts


def _scan_nonbook(
    parquet: pq.ParquetFile,
    item: producer.PublishedComponent,
    identities: Mapping[str, producer.MembershipIdentity],
) -> None:
    table = parquet.read()
    _require(table.num_rows <= EXPECTED_MEMBERSHIPS or item.component == producer.COMPONENT_SCENARIO, "nonbook component unexpectedly large")
    rows = table.to_pylist()
    if item.component == producer.COMPONENT_OFFICIAL_FEE:
        _require(rows == [], "official fee observations unexpectedly exist")
    elif item.component == producer.COMPONENT_SCENARIO:
        _require(rows == list(fee_scenario_rows()), "fee scenario policy changed")
    else:
        _require(len(rows) == 1 and item.native_symbol in identities, "fee gap identity changed")
        expected = {
            **identities[item.native_symbol].row(),
            "required_product": producer.PRODUCT,
            "gap_kind": FEE_GAP_KIND,
            "gap_status": FEE_GAP_KIND,
            "blocking": False,
            "authority_class": FEE_AUTHORITY_CLASS,
            "explained_by": "no_free_reproducible_historical_fee_authority",
        }
        _require(rows[0] == expected, "fee gap semantics changed")


def _scan_components(
    tree: producer._OutputTree,
    components: Sequence[producer.PublishedComponent],
    raw_by_lineage: Mapping[str, tuple[Mapping[str, Any], ...]],
    memberships: Sequence[producer.MembershipIdentity],
) -> tuple[Mapping[str, Any], tuple[Mapping[str, Any], ...]]:
    identities = {item.native_symbol: item for item in memberships}
    _require(
        len(memberships) == len(identities) == EXPECTED_MEMBERSHIPS,
        "membership equation changed",
    )
    intervals: dict[str, list[tuple[int, int]]] = defaultdict(list)
    physical: dict[str, int] = {}
    quote_states: Counter[str] = Counter()
    fee_symbols: set[str] = set()
    for item in components:
        fd = tree.open_final(item.parquet_path)
        try:
            parquet = pq.ParquetFile(f"/proc/self/fd/{fd}")
            _require(parquet.schema_arrow == producer.SCHEMAS[item.component], "encoded component schema changed")
            _require(parquet.metadata.num_rows == item.row_count, "encoded Parquet row metadata changed")
            _require(all(parquet.metadata.row_group(index).num_rows <= SIZING_ROW_BATCH for index in range(parquet.metadata.num_row_groups)), "encoded Parquet row-group cap changed")
            if item.component in {producer.COMPONENT_TICKER, producer.COMPONENT_DEPTH}:
                _require(item.native_symbol in identities, "book partition is outside membership")
                relative = str(item.lineage_path.relative_to(tree.root))
                states, facts = _scan_book(parquet, item, raw_by_lineage[relative], identities[item.native_symbol])
                quote_states.update(states)
                for key, (first, last, count) in facts.items():
                    previous = physical.setdefault(key, count)
                    _require(previous == count, "source physical row domain changed")
                    intervals[key].append((first, last))
            else:
                _scan_nonbook(parquet, item, identities)
                if item.component == producer.COMPONENT_FEE_GAP:
                    _require(item.native_symbol not in fee_symbols, "fee gap identity repeats")
                    fee_symbols.add(item.native_symbol)
        finally:
            os.close(fd)
    source_facts: list[Mapping[str, Any]] = []
    for key in sorted(physical):
        cursor = 0
        ordered_ranges = sorted(intervals[key])
        for first, last in ordered_ranges:
            _require(first == cursor, "source ordinals overlap or are omitted")
            cursor = last + 1
        _require(cursor == physical[key], "source ordinal domain is incomplete")
        source_facts.append(
            {
                "source_key": key,
                "physical_rows": cursor,
                "retained_rows": cursor,
                "first_ordinal": 0,
                "last_ordinal": cursor - 1,
                "partition_ranges": [{"first": first, "last": last} for first, last in ordered_ranges],
            }
        )
    compact = [{"source_key": item["source_key"], "physical_rows": item["physical_rows"]} for item in source_facts]
    _require(set(physical) == {source["source_key"] for values in raw_by_lineage.values() for source in values}, "encoded source coverage changed")
    _require(hashlib.sha256(_canonical_json(compact, newline=False)).hexdigest() == SOURCE_ROW_FACTS_SHA256, "source row-facts identity changed")
    _require(sum(item["physical_rows"] for item in source_facts) == EXPECTED_BOOK_ROWS, "book source row equation changed")
    _require(dict(quote_states) == dict(EXPECTED_QUOTE_STATES), "ticker quote-state counts changed")
    _require(fee_symbols == set(identities), "fee gap identities are incomplete")
    return dict(sorted(quote_states.items())), tuple(source_facts)


def _component_facts(components: Sequence[producer.PublishedComponent]) -> Mapping[str, Mapping[str, int]]:
    result: dict[str, Mapping[str, int]] = {}
    for component in COST_COMPONENTS:
        selected = [item for item in components if item.component == component]
        actual = {
            "partitions": len(selected),
            "rows": sum(item.row_count for item in selected),
            "parquet_bytes": sum(item.parquet_bytes for item in selected),
            "largest_partition_bytes": max((item.parquet_bytes for item in selected), default=0),
        }
        _require(actual == EXPECTED_COMPONENTS[component], f"{component} reviewed component facts changed")
        limits = producer.COMPONENT_LIMITS[component]
        _require(
            actual["partitions"] <= limits["partitions"]
            and actual["parquet_bytes"] <= limits["bytes"]
            and actual["largest_partition_bytes"] <= limits["largest_partition_bytes"],
            f"{component} immutable byte or partition allocation exceeded",
        )
        if component != producer.COMPONENT_TICKER:
            _require(actual["rows"] <= limits["rows"], f"{component} immutable row allocation exceeded")
        result[component] = actual
    _require(sum(value["rows"] for value in result.values()) == EXPECTED_ALL_ROWS, "all-component row equation changed")
    return result


def _validate_source_gaps(
    tree: producer._OutputTree,
    inventory: _Inventory,
    gaps: Sequence[Mapping[str, Any]],
    memberships: Sequence[producer.MembershipIdentity],
) -> Mapping[str, Any]:
    relative = f".source-gaps/{SOURCE_GAP_SHA256}.json"
    entry = next((item for item in inventory.entries if item["path"] == relative), None)
    _require(entry is not None and entry["bytes"] == SOURCE_GAP_BYTES, "source-gap artifact changed")
    document = _read_json(tree, relative, SOURCE_GAP_SHA256, SOURCE_GAP_BYTES)
    identities = {item.native_symbol: item for item in memberships}
    enriched = []
    for gap in gaps:
        symbol = gap.get("symbol")
        _require(type(symbol) is str and symbol in identities, "source gap is outside membership")
        enriched.append({**dict(gap), "membership": identities[symbol].row()})
    expected = {
        "document_type": f"{producer.PRODUCT}_frozen_source_gaps",
        "schema_version": 1,
        "required_product": producer.PRODUCT,
        "manifest_sha256": producer.COST_MANIFEST_SHA256,
        "row_count": EXPECTED_SOURCE_GAPS,
        "gaps": enriched,
    }
    _require(len(gaps) == EXPECTED_SOURCE_GAPS and document == expected, "source-gap facts changed")
    return {"row_count": EXPECTED_SOURCE_GAPS, "path": relative, "sha256": SOURCE_GAP_SHA256, "bytes": SOURCE_GAP_BYTES}


def _completion_document(
    root: Path,
    components: Sequence[producer.PublishedComponent],
    component_facts: Mapping[str, Mapping[str, int]],
    source_facts: Sequence[Mapping[str, Any]],
    quote_states: Mapping[str, int],
    sources: Sequence[producer.RawCostObject],
    source_gap: Mapping[str, Any],
) -> Mapping[str, Any]:
    partitions = [
        {
            "component": item.component,
            "native_symbol": item.native_symbol,
            "utc_month": item.utc_month,
            "row_count": item.row_count,
            "parquet_path": str(item.parquet_path.relative_to(root)),
            "parquet_sha256": item.parquet_sha256,
            "parquet_bytes": item.parquet_bytes,
            "lineage_path": str(item.lineage_path.relative_to(root)),
            "lineage_sha256": item.lineage_sha256,
            "lineage_bytes": item.lineage_bytes,
        }
        for item in sorted(components, key=lambda value: (value.component, value.native_symbol, value.utc_month))
    ]
    parquet_bytes = sum(item.parquet_bytes for item in components)
    lineage_bytes = sum(item.lineage_bytes for item in components)
    document: dict[str, Any] = {
        "document_type": f"{producer.PRODUCT}_product_completion",
        "schema_version": 1,
        "required_product": producer.PRODUCT,
        "schema_sha256": producer.SCHEMA_SHA256,
        "component_schemas": producer.SCHEMA_IDENTITIES,
        "writer_identity": writer_identity(),
        "normalizer_source_sha256": ORIGINAL_PRODUCER_SHA256,
        "normalizer_integration_commit": ORIGINAL_INTEGRATION_COMMIT,
        "finalizer_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "preserved_inventory_sha256": PRESERVED_INVENTORY_SHA256,
        "authority_sha256": {
            "report": producer.REPORT_SHA256,
            "sizing": producer.SIZING_SHA256,
            "cost_manifest": producer.COST_MANIFEST_SHA256,
            "generation0_seal": producer.GENERATION0_SEAL,
            "v3_manifest": producer.V3_MANIFEST_SHA256,
            "membership_completion": producer.MEMBERSHIP_COMPLETION_SHA256,
        },
        "source_equation": {
            "objects": len(sources),
            "compressed_bytes": sum(source.byte_size for source in sources),
            "generation0_objects": sum(source.authority == "accepted_generation_0_completion" for source in sources),
            "recovery_objects": sum(source.authority == "accepted_v3_direct_recovery" for source in sources),
            "physical_rows": EXPECTED_BOOK_ROWS,
            "retained_rows": EXPECTED_BOOK_ROWS,
            "dropped_rows": 0,
            "deduplicated_rows": 0,
        },
        "source_row_facts_sha256": SOURCE_ROW_FACTS_SHA256,
        "source_row_reconciliation": list(source_facts),
        "component_rows": {component: component_facts[component]["rows"] for component in COST_COMPONENTS},
        "component_measured_facts": component_facts,
        "quote_states": quote_states,
        "ticker_row_projection_disposition": {
            "projected_rows": producer.COMPONENT_LIMITS[producer.COMPONENT_TICKER]["rows"],
            "actual_rows": EXPECTED_COMPONENTS[producer.COMPONENT_TICKER]["rows"],
            "excess_rows": EXPECTED_COMPONENTS[producer.COMPONENT_TICKER]["rows"] - producer.COMPONENT_LIMITS[producer.COMPONENT_TICKER]["rows"],
            "status": "EXCEEDED_REVIEWED_EXACT_ARTIFACT_VARIANCE",
            "ordinary_sizing_check_passed": False,
        },
        "encoded_validation_scope": {
            "compressed_raw_objects_rehashed": True,
            "zip_members_expanded": False,
            "csv_rows_parsed": False,
            "parquet_rows_validated": True,
            "independent_complete_csv_to_parquet_value_equality_claimed": False,
        },
        "fee_authority": {"official_historical_rows": 0, "gap_rows": EXPECTED_MEMBERSHIPS, "gap_kind": FEE_GAP_KIND, "missing_fee_is_zero": False},
        "scenario_policy": {"rows": 2, "policy_known_at": FEE_POLICY_KNOWN_AT, "authority_class": FEE_AUTHORITY_CLASS, "historical_observation": False, "historical_upper_bound": False, "charges_each_side": True},
        "frozen_source_gaps": source_gap,
        "partition_count": len(components),
        "projected_partition_ceiling": producer.PROJECTED_PARTITIONS,
        "normalized_allocation_bytes": producer.NORMALIZED_ALLOCATION_BYTES,
        "preserved_inventory": {"files": PRESERVED_FILES, "directories": PRESERVED_DIRECTORIES, "bytes": PRESERVED_BYTES, "sha256": PRESERVED_INVENTORY_SHA256},
        "partitions": partitions,
        "measured_output_bytes": {"parquet": parquet_bytes, "lineage": lineage_bytes, "source_gaps": SOURCE_GAP_BYTES, "completion": 0, "total": 0},
    }
    for _attempt in range(16):
        completion_bytes = len(_canonical_json(document, newline=True))
        total = PRESERVED_BYTES + completion_bytes
        measurement = document["measured_output_bytes"]
        if measurement["completion"] == completion_bytes and measurement["total"] == total:
            break
        measurement["completion"] = completion_bytes
        measurement["total"] = total
    else:
        raise Error("completion byte measurement did not stabilize")
    _require(total <= producer.NORMALIZED_ALLOCATION_BYTES, "normalized allocation including completion exceeded")
    return document


def _finalize_verified_artifacts(
    *,
    sources: Sequence[producer.RawCostObject],
    memberships: Sequence[producer.MembershipIdentity],
    gaps: Sequence[Mapping[str, Any]],
    output_root: Path,
    hooks: FinalizationHooks = FinalizationHooks(),
    authority_reproof: Callable[[], None] | None = None,
) -> CostFinalizationResult:
    _verify_producer()
    producer._no_symlinks(output_root, "preserved output root")
    _require(output_root.is_dir(), "preserved output root is absent")
    staging = output_root / ".staging"
    producer._no_symlinks(staging, "preserved staging directory")
    _require(staging.is_dir(), "preserved staging directory is missing or unsafe")
    _source_equation(sources)
    _authenticate_sources(sources)
    tree = producer._OutputTree(output_root)
    try:
        before = _inventory(tree)
        components, raw_by_lineage = _parse_lineages(tree, before, sources)
        facts = _component_facts(components)
        source_gap = _validate_source_gaps(tree, before, gaps, memberships)
        quote_states, source_facts = _scan_components(tree, components, raw_by_lineage, memberships)
        if authority_reproof is not None:
            authority_reproof()
        _authenticate_sources(sources)
        document = _completion_document(tree.root, components, facts, source_facts, quote_states, sources, source_gap)
        body = _canonical_json(document, newline=True)
        digest = hashlib.sha256(body).hexdigest()
        expected_relative = f".complete/{digest}.json"
        _require(before.completion in {None, expected_relative}, "existing completion conflicts with verified result")
        _inventory(tree)
        tree.only_completion(f"{digest}.json")

        def before_publish(kind: str, stage: Path, destination: Path) -> None:
            if hooks.before_completion_publish is not None:
                hooks.before_completion_publish(stage, destination)

        path, observed, size, reused = producer._publish_json(
            tree,
            document,
            (".complete",),
            "cost-finalization-completion",
            producer.PublicationHooks(before_publish=before_publish),
        )
        _require(observed == digest and size == len(body), "published completion identity changed")
        after = _inventory(tree)
        _require(after.completion == expected_relative and len(after.files) == PRESERVED_FILES + 1, "final output inventory changed")
        completion_entry = _file_entry(tree, expected_relative)
        _require(completion_entry["sha256"] == digest and completion_entry["bytes"] == size, "completion final reproof failed")
        return CostFinalizationResult(path, digest, reused, len(components), EXPECTED_BOOK_ROWS)
    finally:
        tree.close()


def _load_authorities(
    *,
    report_path: Path,
    sizing_path: Path,
    generation0_state: Path,
    generation0_content_root: Path,
    v3_manifest: Path,
    recovery_root: Path,
    membership_root: Path,
) -> tuple[
    tuple[producer.RawCostObject, ...],
    tuple[producer.MembershipIdentity, ...],
    tuple[Mapping[str, Any], ...],
]:
    _verify_producer()
    report = producer._read_pinned(report_path, producer.REPORT_SHA256, producer.MAX_REPORT_BYTES)
    sizing = producer._read_pinned(sizing_path, producer.SIZING_SHA256, producer.MAX_SIZING_BYTES)
    selected, gaps = producer._report_manifest(report)
    producer._validate_sizing(sizing)
    generation0 = producer.load_generation0_cost_sources(generation0_state, generation0_content_root, selected)
    recovery = producer.load_recovery_cost_sources(v3_manifest, recovery_root, selected)
    sources = tuple(sorted((*generation0, *recovery), key=lambda value: value.source_key))
    _require({source.source_key for source in sources} == selected, "authority union does not equal frozen cost manifest")
    _require(not ({source.source_key for source in generation0} & {source.source_key for source in recovery}), "cost authorities overlap")
    producer._manifest_reproof(sources, gaps)
    memberships = producer.load_membership_identities(membership_root)
    return sources, memberships, gaps


def finalize_from_authorities(
    *,
    report_path: Path,
    sizing_path: Path,
    generation0_state: Path,
    generation0_content_root: Path,
    v3_manifest: Path,
    recovery_root: Path,
    membership_root: Path,
    output_root: Path,
    hooks: FinalizationHooks = FinalizationHooks(),
) -> CostFinalizationResult:
    authority_arguments = {
        "report_path": report_path,
        "sizing_path": sizing_path,
        "generation0_state": generation0_state,
        "generation0_content_root": generation0_content_root,
        "v3_manifest": v3_manifest,
        "recovery_root": recovery_root,
        "membership_root": membership_root,
    }
    sources, memberships, gaps = _load_authorities(**authority_arguments)

    def reprove() -> None:
        repeated_sources, repeated_memberships, repeated_gaps = _load_authorities(
            **authority_arguments
        )
        _require(
            repeated_sources == sources
            and repeated_memberships == memberships
            and repeated_gaps == gaps,
            "authenticated authorities changed during finalization",
        )

    return _finalize_verified_artifacts(
        sources=sources,
        memberships=memberships,
        gaps=gaps,
        output_root=output_root,
        hooks=hooks,
        authority_reproof=reprove,
    )
