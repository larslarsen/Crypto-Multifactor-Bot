"""Offline, complete CEX-002 Nautilus transport check for one sealed candidate.

This checker creates a private scratch catalog.  Its transport clocks are the
checker's observation time and are never historical source-availability facts.
It does not admit the release to the production dataset catalog.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import importlib.metadata
import json
import os
import stat
import sys
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar, Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq
from nautilus_trader.model import (
    Bar,
    BarAggregation,
    BarSpecification,
    BarType,
    CustomData,
    DataType,
    InstrumentId,
    Price,
    PriceType,
    Quantity,
    Symbol,
    Venue,
    register_custom_data_class,
)
from nautilus_trader.persistence import ParquetDataCatalog

from cryptofactors.catalog.dataset.cex002_reference_release import (
    BUNDLE_ROOT_RELATIVE,
    COMPONENT_KEYS,
    OPERATING_RESERVE_BYTES,
    PROOF_DOCUMENT,
    PROOF_KEYS,
    PROOF_MAX_BYTES,
    PROOF_SCOPE,
    RELEASE_METADATA_REMAINDER_BYTES,
    _anchor,
    _encode_logical,
    _footer_from_partition,
    _hash_fd,
    _hash_file,
    _load_prepared,
    _registry_contracts,
    _rename_noreplace,
    _release_charge,
    _relative,
    _render_timestamp,
    _snapshot,
    _time_plan,
    _timestamp_sort_key,
    seal_code_identity,
)
CANDIDATE_SHA256 = "8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34"
SOURCE_COMMIT = "1f5629badfa0e8af6338fbeb019a5f7e60b6a324"
NAUTILUS_VERSION = "2.0.0rc3"
PYARROW_VERSION = "25.0.0"
MAX_ROWS = 65_536
ARROW_BATCH_ROWS = 2_048
MAX_BATCH_BYTES = 16 * 2**20
SCRATCH_CAP_BYTES = 256 * 2**20
PUBLICATION_ALLOWANCE_BYTES = 8_388_608
EXPECTED_FILES = 423_446
EXPECTED_ROWS = 1_165_116_869
TYPE_NAME = "Cex002ReferenceRowV1"
_U64 = 2**64 - 1
_SCHEMA = pa.schema(
    [
        pa.field("ordinal", pa.uint64(), nullable=False),
        pa.field("payload", pa.string(), nullable=False),
        pa.field("payload_sha256", pa.string(), nullable=False),
        pa.field("ts_event", pa.uint64(), nullable=False),
        pa.field("ts_init", pa.uint64(), nullable=False),
    ]
)
_REGISTERED = False


class ConsumerCheckError(ValueError):
    """A source, transport, proof or resource condition prevented PASS."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ConsumerCheckError(reason)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


@dataclass(frozen=True, slots=True)
class Cex002ReferenceRow:
    """One authenticated row, with its explicit source ordinal and typed fields."""

    ordinal: int
    payload: str
    payload_sha256: str
    ts_event: int
    ts_init: int
    _schema: ClassVar[pa.Schema] = _SCHEMA

    def __post_init__(self) -> None:
        _require(type(self.ordinal) is int and 0 <= self.ordinal <= _U64, "invalid row ordinal")
        _require(type(self.payload) is str, "invalid row payload")
        _require(type(self.payload_sha256) is str and _sha(self.payload.encode("ascii")) == self.payload_sha256, "row payload SHA mismatch")
        _require(type(self.ts_event) is int and 0 <= self.ts_event <= _U64, "invalid transport event clock")
        _require(type(self.ts_init) is int and 0 <= self.ts_init <= _U64, "invalid transport initialization clock")

    @classmethod
    def type_name_static(cls) -> str:
        return TYPE_NAME

    def to_json(self) -> str:
        return _json({
            "ordinal": self.ordinal, "payload": self.payload,
            "payload_sha256": self.payload_sha256,
            "ts_event": self.ts_event, "ts_init": self.ts_init,
        })

    @classmethod
    def from_json(cls, value: object) -> Cex002ReferenceRow:
        if isinstance(value, (bytes, bytearray)):
            value = bytes(value).decode("ascii")
        if isinstance(value, str):
            value = json.loads(value)
        _require(type(value) is dict and set(value) == {"ordinal", "payload", "payload_sha256", "ts_event", "ts_init"}, "invalid Nautilus row JSON")
        assert isinstance(value, dict)
        return cls(**value)

    def encode_record_batch_py(self, items: Sequence[Cex002ReferenceRow]) -> pa.RecordBatch:
        _require(0 < len(items) <= MAX_ROWS, "custom Arrow batch row bound exceeded")
        return pa.RecordBatch.from_pylist(
            [{"ordinal": row.ordinal, "payload": row.payload,
              "payload_sha256": row.payload_sha256, "ts_event": row.ts_event,
              "ts_init": row.ts_init} for row in items], schema=_SCHEMA,
        )

    @classmethod
    def decode_record_batch_py(cls, metadata: object, batch: object) -> list[Cex002ReferenceRow]:
        _require(isinstance(metadata, Mapping) and metadata.get("type_name") == TYPE_NAME, "custom metadata type mismatch")
        _require(isinstance(batch, pa.RecordBatch), "custom readback is not an Arrow batch")
        assert isinstance(batch, pa.RecordBatch)
        _require(set(batch.schema.names) in (set(_SCHEMA.names), set(_SCHEMA.names) | {"data_type"}), "custom Arrow fields changed")
        for schema_field in _SCHEMA:
            actual = batch.schema.field(schema_field.name).type
            if schema_field.name in {"payload", "payload_sha256"}:
                _require(pa.types.is_string(actual) or pa.types.is_large_string(actual) or pa.types.is_string_view(actual), "custom Arrow payload type changed")
            else:
                _require(actual == schema_field.type, "custom Arrow field type changed")
        _require(batch.num_rows <= MAX_ROWS, "custom readback batch row bound exceeded")
        return [cls.from_json({key: row[key] for key in _SCHEMA.names}) for row in batch.to_pylist()]


def register_row_data() -> None:
    global _REGISTERED
    if not _REGISTERED:
        register_custom_data_class(Cex002ReferenceRow)
        _REGISTERED = True


def _portable(value: Any, kind: pa.DataType) -> Any:
    if value is None:
        return None
    if pa.types.is_decimal(kind):
        return format(value, f".{kind.scale}f")
    if pa.types.is_timestamp(kind) or pa.types.is_integer(kind):
        return int(value)
    if pa.types.is_dictionary(kind):
        return _portable(value, kind.value_type)
    if pa.types.is_list(kind) or pa.types.is_large_list(kind):
        return [_portable(item, kind.value_type) for item in value]
    return value


def _restore(value: Any, kind: pa.DataType) -> Any:
    if value is None:
        return None
    if pa.types.is_decimal(kind):
        _require(type(value) is str, "decimal was not transported as exact text")
        return Decimal(value)
    if pa.types.is_timestamp(kind) or pa.types.is_integer(kind):
        _require(type(value) is int, "integer or timestamp type changed")
        return value
    if pa.types.is_dictionary(kind):
        return _restore(value, kind.value_type)
    if pa.types.is_list(kind) or pa.types.is_large_list(kind):
        _require(type(value) is list, "list type changed")
        return [_restore(item, kind.value_type) for item in value]
    if pa.types.is_boolean(kind):
        _require(type(value) is bool, "boolean type changed")
    if pa.types.is_string(kind) or pa.types.is_large_string(kind):
        _require(type(value) is str, "string type changed")
    return value


def _row_tokens(values: Sequence[Any], schema: pa.Schema) -> bytes:
    _require(len(values) == len(schema), "row width changed")
    return b"".join(_encode_logical(value, field.type) for value, field in zip(values, schema, strict=True))


def _row_payload(values: Sequence[Any], schema: pa.Schema) -> str:
    return _json([_portable(value, field.type) for value, field in zip(values, schema, strict=True)])


def _decoded_payload(payload: str, schema: pa.Schema) -> tuple[Any, ...]:
    data = json.loads(payload)
    _require(type(data) is list and len(data) == len(schema), "readback row width changed")
    return tuple(_restore(value, field.type) for value, field in zip(data, schema, strict=True))


@dataclass(slots=True)
class _Values:
    schema: pa.Schema
    digest: Any
    count: int = 0
    earliest: tuple[int, str] | None = None
    latest: tuple[int, str] | None = None
    time_indexes: tuple[int, ...] = field(init=False)
    time_kind: str = field(init=False)

    def __post_init__(self) -> None:
        self.time_indexes, self.time_kind = _time_plan(self.schema)

    def add(self, values: Sequence[Any]) -> None:
        self.digest.update(_row_tokens(values, self.schema))
        for index in self.time_indexes:
            value = values[index]
            if value is None:
                continue
            field = self.schema.field(index)
            if self.time_kind == "timestamp":
                pair = (_timestamp_sort_key(value, field.type.unit), _render_timestamp(value, field.type.unit))
            else:
                pair = (int(value), str(int(value)))
            if self.earliest is None or pair < self.earliest:
                self.earliest = pair
            if self.latest is None or pair > self.latest:
                self.latest = pair
        self.count += 1

    def times(self) -> tuple[str | None, str | None, str | None]:
        if not self.time_indexes:
            return None, None, "non_temporal_component"
        if self.earliest is None:
            return None, None, "empty_component"
        assert self.latest is not None
        return self.earliest[1], self.latest[1], None


def _physical_files(root: Path) -> tuple[tuple[Path, int], ...]:
    """Inspect only a fresh checker-owned scratch tree; refuse special paths."""
    files: list[tuple[Path, int]] = []
    for directory, names, filenames in os.walk(root, followlinks=False):
        for name in names:
            path = Path(directory) / name
            _require(stat.S_ISDIR(path.lstat().st_mode), "unsafe scratch directory")
        for name in filenames:
            path = Path(directory) / name
            facts = path.lstat()
            _require(stat.S_ISREG(facts.st_mode), "unsafe scratch file")
            files.append((path, max(facts.st_size, facts.st_blocks * 512)))
    return tuple(files)


def _physical_dirs(root: Path) -> set[Path]:
    directories = set()
    for directory, names, _filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        _require(stat.S_ISDIR(current.lstat().st_mode), "scratch directory changed")
        directories.add(current)
        for name in names:
            _require(stat.S_ISDIR((current / name).lstat().st_mode), "unsafe scratch directory")
    return directories


def _scratch_bytes(root: Path) -> int:
    measured = sum(size for _, size in _physical_files(root))
    _require(measured <= SCRATCH_CAP_BYTES, "scratch physical byte cap exceeded")
    return measured


@dataclass(frozen=True, slots=True)
class _ScratchBinding:
    directories: tuple[tuple[Path, int, int], ...]
    files: tuple[tuple[Path, int, int, int, str], ...]


def _bind_written(root: Path, batch: Path, written: Sequence[str]) -> _ScratchBinding:
    """Bind exactly the catalog-returned files and every containing directory."""
    _require(batch.parent == root and bool(written), "unowned scratch batch")
    listed = _physical_files(batch)
    paths = {path for path, _size in listed}
    reported: set[Path] = set()
    for value in written:
        path = Path(value)
        if not path.is_absolute():
            path = batch / path
        _require(path.is_relative_to(batch) and path != batch and ".." not in path.parts, "Nautilus returned an unsafe file path")
        reported.add(path)
    _require(paths == reported and len(reported) == len(written), "unexpected scratch file or missing catalog write")
    directories = {root, batch}
    for path in reported:
        directories.update(parent for parent in path.parents if parent == batch or batch in parent.parents)
    _require(_physical_dirs(batch) | {root} == directories, "unexpected scratch directory")
    dir_bindings = []
    for directory in sorted(directories):
        facts = directory.lstat()
        _require(stat.S_ISDIR(facts.st_mode), "scratch directory changed")
        dir_bindings.append((directory, facts.st_dev, facts.st_ino))
    file_bindings = []
    for path in sorted(reported):
        facts = path.lstat()
        _require(stat.S_ISREG(facts.st_mode), "scratch file changed")
        digest, size, inode, device = _hash_file(path)
        _require((size, inode, device) == (facts.st_size, facts.st_ino, facts.st_dev), "scratch file changed while binding")
        file_bindings.append((path, device, inode, size, digest))
    return _ScratchBinding(tuple(dir_bindings), tuple(file_bindings))


def _check_bound(binding: _ScratchBinding) -> None:
    for directory, device, inode in binding.directories:
        facts = directory.lstat()
        _require(stat.S_ISDIR(facts.st_mode) and (facts.st_dev, facts.st_ino) == (device, inode), "scratch directory binding changed")
    for path, device, inode, size, digest in binding.files:
        facts = path.lstat()
        _require(stat.S_ISREG(facts.st_mode) and (facts.st_dev, facts.st_ino, facts.st_size) == (device, inode, size), "scratch file binding changed")
        _require(_hash_file(path)[0] == digest, "scratch file bytes changed")


def _free(path: Path) -> int:
    info = os.statvfs(path)
    return int(info.f_bavail) * int(info.f_frsize)


def _reserve(path: Path, incoming: int) -> None:
    _require(_free(path) >= OPERATING_RESERVE_BYTES + incoming, "operating reserve would be consumed")


def _fresh_scratch(path: Path, repo: Path) -> Path:
    _require(path.is_absolute(), "scratch root must be absolute")
    _require(not path.exists() and not path.is_symlink(), "scratch root must be fresh")
    _require(not path.is_relative_to(repo) and not repo.is_relative_to(path), "scratch root must be separate from repository")
    for parent in (path.parent, *path.parent.parents):
        facts = parent.lstat()
        _require(stat.S_ISDIR(facts.st_mode), "scratch ancestor must be a real directory")
    path.mkdir(mode=0o700)
    _require(_scratch_bytes(path) == 0, "scratch root is not empty")
    return path


def _owned_cleanup(root: Path, batch: Path, binding: _ScratchBinding) -> None:
    """Remove only regular files produced inside this run's private batch root."""
    _require(batch.parent == root and batch.is_dir() and not batch.is_symlink(), "scratch batch changed")
    _require(bool(binding.files), "Nautilus produced no scratch files")
    _check_bound(binding)
    _require(_physical_dirs(batch) | {root} == {item[0] for item in binding.directories}, "unexpected scratch directory before cleanup")
    _require({path for path, _size in _physical_files(batch)} == {record[0] for record in binding.files}, "unexpected scratch file before cleanup")
    for path, _device, _inode, _size, _digest in binding.files:
        path.unlink()
    for directory, _names, _filenames in os.walk(batch, topdown=False, followlinks=False):
        Path(directory).rmdir()
    _scratch_bytes(root)


def _catalog_type(identifier: str) -> DataType:
    return DataType(TYPE_NAME, metadata={"schema_version": "1", "transport_clock": "validation_observation_only"}, identifier=identifier)


def _decimal_places(value: object) -> int:
    _require(isinstance(value, Decimal) and value.is_finite(), "native numeric projection is not a finite Decimal")
    rendered = format(value, "f")
    return len(rendered.split(".", 1)[1].rstrip("0")) if "." in rendered else 0


def _native_bar(
    values: Sequence[Any], schema: pa.Schema, observed_ns: int,
    price_precision: int | None = None, size_precision: int | None = None,
) -> Bar:
    row = dict(zip(schema.names, values, strict=True))
    required = {"venue_symbol", "open_time", "close_time", "open", "high", "low", "close", "volume"}
    _require(required <= set(row), "bar table lacks native projection fields")
    symbol = row["venue_symbol"]
    _require(type(symbol) is str and symbol and "." not in symbol, "invalid venue-native bar symbol")
    close_ms = row["close_time"]
    _require(type(close_ms) is int and close_ms >= 0 and close_ms * 1_000_000 <= _U64, "bar close_time is not representable")
    instrument = InstrumentId(Symbol(symbol), Venue("BINANCE"))
    bar_type = BarType(instrument, BarSpecification(1, BarAggregation.HOUR, PriceType.LAST))
    if price_precision is None:
        price_precision = max(_decimal_places(row[name]) for name in ("open", "high", "low", "close"))
    if size_precision is None:
        size_precision = _decimal_places(row["volume"])
    prices = [Price.from_decimal_dp(row[name], price_precision) for name in ("open", "high", "low", "close")]
    quantity = Quantity.from_decimal_dp(row["volume"], size_precision)
    for name, price in zip(("open", "high", "low", "close"), prices, strict=True):
        _require(price.as_decimal() == row[name], f"native {name} conversion lost precision")
    _require(quantity.as_decimal() == row["volume"], "native volume conversion lost precision")
    return Bar(bar_type, *prices, quantity, close_ms * 1_000_000, observed_ns)


def _native_key(bar: Bar) -> tuple[Any, ...]:
    return (
        str(bar.bar_type), bar.open.as_decimal(), bar.high.as_decimal(),
        bar.low.as_decimal(), bar.close.as_decimal(), bar.volume.as_decimal(),
        bar.ts_event, bar.ts_init,
    )


def _roundtrip_batch(
    scratch: Path, sequence: int, schema: pa.Schema, rows: Sequence[tuple[int, tuple[Any, ...]]],
    *, native_bars: bool,
    payloads: Sequence[str] | None = None,
) -> list[tuple[int, tuple[Any, ...]]]:
    _require(0 < len(rows) <= MAX_ROWS, "roundtrip batch row bound exceeded")
    batch = scratch / f"batch-{sequence:012d}"
    batch.mkdir(mode=0o700)
    register_row_data()
    catalog = ParquetDataCatalog(str(batch))
    identifier = _sha(str(batch).encode("utf-8"))
    data_type = _catalog_type(identifier)
    observed = time.time_ns()
    wrappers = []
    for index, (ordinal, values) in enumerate(rows):
        payload = payloads[index] if payloads is not None else _row_payload(values, schema)
        inner = Cex002ReferenceRow(ordinal, payload, _sha(payload.encode("ascii")), observed, observed)
        wrappers.append(CustomData(data_type, inner))
    _require(_scratch_bytes(scratch) + 8 * sum(len(item.data.payload) for item in wrappers) + 16 * 2**20 <= SCRATCH_CAP_BYTES, "scratch prewrite estimate exceeds cap")
    _reserve(scratch, SCRATCH_CAP_BYTES)
    written = [catalog.write_custom_data(wrappers)]
    binding = _bind_written(scratch, batch, written)
    _scratch_bytes(scratch)
    fresh = ParquetDataCatalog(str(batch))
    queried = fresh.query_custom_data(TYPE_NAME, identifiers=[identifier])
    _require(len(queried) == len(rows) and len(queried) <= MAX_ROWS, "custom catalog readback count changed")
    observed_rows: dict[int, tuple[Any, ...]] = {}
    for wrapper in queried:
        _require(isinstance(wrapper, CustomData), "custom catalog did not return CustomData")
        _require(wrapper.data_type.type_name == TYPE_NAME and wrapper.data_type.identifier == identifier, "custom catalog identity changed")
        _require(dict(wrapper.data_type.metadata) == dict(data_type.metadata), "custom catalog metadata changed")
        inner = wrapper.data
        _require(isinstance(inner, Cex002ReferenceRow), "custom catalog returned wrong registered class")
        _require(inner.ordinal not in observed_rows, "duplicate readback ordinal")
        _require((wrapper.ts_event, wrapper.ts_init) == (observed, observed), "transport observation clock changed")
        decoded = _decoded_payload(inner.payload, schema)
        _require(inner.payload == _row_payload(decoded, schema), "readback payload is not canonical typed data")
        observed_rows[inner.ordinal] = decoded
    _require(set(observed_rows) == {ordinal for ordinal, _ in rows}, "custom catalog omitted or substituted ordinals")
    returned = [(ordinal, observed_rows[ordinal]) for ordinal, _ in rows]
    for (_ordinal, source), (_returned_ordinal, value) in zip(rows, returned, strict=True):
        _require(_row_tokens(source, schema) == _row_tokens(value, schema), "custom catalog changed typed row")
    if native_bars:
        named = [dict(zip(schema.names, values, strict=True)) for _, values in rows]
        price_precision = max(_decimal_places(row[name]) for row in named for name in ("open", "high", "low", "close"))
        size_precision = max(_decimal_places(row["volume"]) for row in named)
        expected = [_native_bar(values, schema, observed, price_precision, size_precision) for _, values in rows]
        _check_bound(binding)
        written.append(catalog.write_bars(expected))
        _check_bound(binding)
        binding = _bind_written(scratch, batch, written)
        _scratch_bytes(scratch)
        native_readback = ParquetDataCatalog(str(batch)).query_bars(
            identifiers=sorted({str(bar.bar_type) for bar in expected})
        )
        _require(len(native_readback) == len(expected), "native bar catalog count changed")
        _require(sorted(map(_native_key, native_readback)) == sorted(map(_native_key, expected)), "native Bar readback changed")
    _owned_cleanup(scratch, batch, binding)
    return returned


def _stream_table(
    scratch: Path, sequence: int, path: Path, spec: Any, native_bars: bool,
) -> tuple[dict[str, Any], int]:
    parquet = pq.ParquetFile(path)
    schema = parquet.schema_arrow
    source = _Values(schema, hashlib.sha256())
    returned = _Values(schema, hashlib.sha256())
    pending: list[tuple[int, tuple[Any, ...]]] = []
    pending_payloads: list[str] = []
    pending_bytes = 0

    def flush() -> None:
        nonlocal sequence, pending_bytes
        if not pending:
            return
        for _ordinal, values in _roundtrip_batch(scratch, sequence, schema, pending,
                                                  native_bars=native_bars, payloads=pending_payloads):
            returned.add(values)
        sequence += 1
        pending.clear()
        pending_payloads.clear()
        pending_bytes = 0

    for batch in parquet.iter_batches(batch_size=ARROW_BATCH_ROWS):
        _require(batch.num_rows <= MAX_ROWS and batch.nbytes <= MAX_BATCH_BYTES, "source Arrow batch exceeds bound")
        columns = [
            batch.column(index).cast(pa.int64()).to_pylist()
            if pa.types.is_timestamp(field.type) else batch.column(index).to_pylist()
            for index, field in enumerate(schema)
        ]
        for row_index in range(batch.num_rows):
            values = tuple(column[row_index] for column in columns)
            row_bytes = _row_payload(values, schema).encode("ascii")
            _require(len(row_bytes) <= MAX_BATCH_BYTES, "one row exceeds finite transport bound")
            if pending and (len(pending) >= MAX_ROWS or pending_bytes + len(row_bytes) > MAX_BATCH_BYTES):
                flush()
            ordinal = source.count
            source.add(values)
            pending.append((ordinal, values))
            pending_payloads.append(row_bytes.decode("ascii"))
            pending_bytes += len(row_bytes)
    flush()
    _require(source.count == spec.rows == returned.count == parquet.metadata.num_rows, "source or readback table row count changed")
    _require(source.digest.hexdigest() == returned.digest.hexdigest(), "source and Nautilus typed digests differ")
    _require(source.times() == returned.times(), "source and Nautilus time bounds differ")
    start, end, reason = source.times()
    component = {
        "relative_path": spec.relative_path, "physical_sha256": spec.sha256,
        "physical_bytes": spec.bytes, "kind": "table",
        "source_row_count": source.count, "readback_row_count": returned.count,
        "source_value_sha256": source.digest.hexdigest(),
        "roundtrip_value_sha256": returned.digest.hexdigest(),
        "time_start": start, "time_end": end, "time_absence_reason": reason,
        "value_identity": "typed_row_digest",
    }
    _require(set(component) == COMPONENT_KEYS, "table proof shape changed")
    return component, sequence


def _metadata_component(spec: Any) -> dict[str, Any]:
    component = {
        "relative_path": spec.relative_path, "physical_sha256": spec.sha256,
        "physical_bytes": spec.bytes, "kind": "metadata",
        "source_row_count": 0, "readback_row_count": 0,
        "source_value_sha256": spec.sha256, "roundtrip_value_sha256": spec.sha256,
        "time_start": None, "time_end": None,
        "time_absence_reason": "non_temporal_component", "value_identity": "metadata_bytes",
    }
    _require(set(component) == COMPONENT_KEYS and spec.rows == 0, "metadata proof shape changed")
    return component


def _proof_stage(repo: Path) -> tuple[Path, Any]:
    directory = repo / BUNDLE_ROOT_RELATIVE / ".proofs"
    for ancestor in (directory.parent, *directory.parent.parents):
        facts = ancestor.lstat()
        _require(stat.S_ISDIR(facts.st_mode), "unsafe proof ancestor")
    if not directory.exists():
        directory.mkdir(mode=0o700)
    _require(directory.is_dir() and not directory.is_symlink(), "unsafe proof directory")
    stage = directory / f".stage-{uuid.uuid4().hex}"
    stream = stage.open("xb")
    return stage, stream


def _write_proof_chunk(stream: Any, body: bytes, digest: Any, length: int) -> int:
    length += len(body)
    _require(length <= PROOF_MAX_BYTES, "proof exceeds the 512 MiB cap")
    stream.write(body)
    digest.update(body)
    return length


def _seal_proof(stage: Path, digest: str, length: int, writer_fd: int | None = None) -> Path:
    final = stage.parent / f"{digest}.json"
    descriptor = os.open(stage.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    held: int | None = None
    try:
        held = os.open(stage, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        actual, size, inode, device = _hash_fd(held)
        _require((actual, size) == (digest, length), "proof stage changed before seal")
        if writer_fd is not None:
            writer = os.fstat(writer_fd)
            _require((writer.st_dev, writer.st_ino, writer.st_size) == (device, inode, length), "proof stage differs from original writer")
        before = stage.lstat()
        _require((before.st_dev, before.st_ino) == (device, inode), "proof stage path changed")
        try:
            _rename_noreplace(descriptor, stage.name, final.name)
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                raise ConsumerCheckError("proof content-address collision; no clobber") from exc
            raise
        after = final.lstat()
        _require(stat.S_ISREG(after.st_mode) and (after.st_dev, after.st_ino, after.st_size) == (device, inode, length), "proof rename identity changed")
        os.fsync(descriptor)
    finally:
        if held is not None:
            os.close(held)
        os.close(descriptor)
    return final


def _restore_failed_stage(stage: Path, digest: str, writer_identity: tuple[int, int]) -> None:
    """Move a newly renamed but failed seal back to its private HOLD stage."""
    final = stage.parent / f"{digest}.json"
    if stage.exists() or not final.exists():
        return
    facts = final.lstat()
    _require(stat.S_ISREG(facts.st_mode) and (facts.st_dev, facts.st_ino) == writer_identity, "failed proof final path changed")
    directory = os.open(stage.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        _rename_noreplace(directory, final.name, stage.name)
        os.fsync(directory)
    finally:
        os.close(directory)


def _progress(stage: str, files: int, rows: int, began: float, **extra: Any) -> None:
    sys.stderr.write(_json({"stage": stage, "completed_files": files, "completed_rows": rows,
                            "elapsed_seconds": round(time.monotonic() - began, 3), **extra}) + "\n")
    sys.stderr.flush()


def check_release(repo: Path, candidate_sha256: str, checker_source_sha256: str, scratch_root: Path) -> tuple[Path, str]:
    began = time.monotonic()
    _require(candidate_sha256 == CANDIDATE_SHA256, "candidate SHA is not the accepted pin")
    _require(importlib.metadata.version("nautilus-trader") == NAUTILUS_VERSION, "Nautilus version pin mismatch")
    _require(pa.__version__ == PYARROW_VERSION, "PyArrow version pin mismatch")
    _require(sys.version_info[:2] == (3, 13), "Python 3.13 is required")
    executing = Path(__file__)
    _require(_sha(executing.read_bytes()) == checker_source_sha256, "checker source SHA mismatch")
    root = _anchor(repo)
    _require(not executing.is_symlink(), "checker source path is a symlink")
    runtime_sources = {
        "src/cryptofactors/catalog/dataset/cex002_reference_release.py": root / "src/cryptofactors/catalog/dataset/cex002_reference_release.py",
        "src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py": root / "src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py",
        "scripts/research/publish_binance_usdm_harmonic_bundle.py": root / "scripts/research/publish_binance_usdm_harmonic_bundle.py",
    }
    code = seal_code_identity(root, SOURCE_COMMIT, bind_runtime=True, executing=runtime_sources)
    descriptor, manifests = _load_prepared(root, candidate_sha256)
    _require(descriptor.get("consumable") is False, "candidate is not non-consumable preparation")
    _require(all(item.code == code for item in manifests), "manifest code identity drift")
    _require(sum(len(item.files) for item in manifests) == EXPECTED_FILES, "release file closure changed")
    _require(sum(spec.rows for item in manifests for spec in item.files) == EXPECTED_ROWS, "release row closure changed")
    bundle_bytes, charged, _incoming, subtotals = _release_charge(root, manifests, [])
    _require(charged + PROOF_MAX_BYTES + SCRATCH_CAP_BYTES + PUBLICATION_ALLOWANCE_BYTES <= RELEASE_METADATA_REMAINDER_BYTES, "combined release resource cap exceeded")
    _require(scratch_root.is_absolute(), "scratch root must be absolute")
    _reserve(root, PROOF_MAX_BYTES + PUBLICATION_ALLOWANCE_BYTES + subtotals["sqlite_bytes"]
             + (SCRATCH_CAP_BYTES if root.stat().st_dev == scratch_root.parent.stat().st_dev else 0))
    scratch = _fresh_scratch(scratch_root, root)
    _reserve(scratch, SCRATCH_CAP_BYTES)
    _progress("authenticated_descriptor", 0, 0, began, candidate_sha256=candidate_sha256)
    stage, stream = _proof_stage(root)
    writer_facts = os.fstat(stream.fileno())
    writer_identity = (writer_facts.st_dev, writer_facts.st_ino)
    digest = hashlib.sha256()
    length = 0
    completed_files = 0
    completed_rows = 0
    sequence = 0
    status_offset: int | None = None
    patched = False
    final_sha: str | None = None
    try:
        prefix = _json({
            "document_type": PROOF_DOCUMENT, "schema_version": 1,
            "status": "HOLD", "scope": PROOF_SCOPE,
            "candidate_sha256": candidate_sha256,
            "checker_source_sha256": checker_source_sha256,
            "nautilus_version": NAUTILUS_VERSION,
        })[:-1].encode("ascii") + b',"datasets":['
        length = _write_proof_chunk(stream, prefix, digest, length)
        status_offset = prefix.index(b'"HOLD"') + 1
        _require(set(json.loads(prefix.split(b',"datasets":[')[0] + b"}")) | {"datasets"} == PROOF_KEYS, "proof root contract changed")
        for manifest_index, manifest in enumerate(manifests):
            contracts = _registry_contracts(manifest)
            if manifest_index:
                length = _write_proof_chunk(stream, b",", digest, length)
            head = b'{"dataset_id":' + _json(manifest.dataset_id).encode("ascii") + b',"components":['
            length = _write_proof_chunk(stream, head, digest, length)
            for file_index, spec in enumerate(manifest.files):
                path = _relative(root, spec.relative_path)
                before = _snapshot(root, spec.relative_path)
                _require((before.sha256, before.byte_size) == (spec.sha256, spec.bytes), "referenced file changed")
                kind = spec.partition.get("kind")
                _require(kind in {"table", "metadata"}, "unrecognized component kind")
                if kind == "table":
                    _require(spec.partition.get("schema_ref") in contracts, "schema reference changed")
                    _footer_from_partition(path, spec, contracts)
                    native_bars = False
                    if manifest.dataset_type == "binance_usdm_bar_1h":
                        _require(spec.partition.get("role") == "partition", "bar table role is not the accepted partition role")
                        _require("component" in spec.partition and type(spec.partition["component"]) is str
                                 and spec.partition["component"] in {"", "quality_gap"},
                                 "bar table component is not the accepted primary or quality_gap tag")
                        native_bars = spec.partition["component"] == ""
                    if native_bars:
                        _require(
                            {"venue_symbol", "open_time", "close_time", "open", "high", "low", "close", "volume"}
                            <= set(pq.ParquetFile(path).schema_arrow.names),
                            "declared bar partition lacks the mandatory native projection",
                        )
                    component, sequence = _stream_table(
                        scratch, sequence, path, spec, native_bars,
                    )
                else:
                    component = _metadata_component(spec)
                after = _snapshot(root, spec.relative_path)
                _require(after == before, "source file changed during transport")
                if file_index:
                    length = _write_proof_chunk(stream, b",", digest, length)
                length = _write_proof_chunk(stream, _json(component).encode("ascii"), digest, length)
                completed_files += 1
                completed_rows += component["source_row_count"]
                if completed_files % 1024 == 0:
                    _progress("roundtrip", completed_files, completed_rows, began)
            length = _write_proof_chunk(stream, b"]}", digest, length)
        length = _write_proof_chunk(stream, b"]}\n", digest, length)
        _require(completed_files == EXPECTED_FILES and completed_rows == EXPECTED_ROWS, "release traversal incomplete")
        _require(_scratch_bytes(scratch) == 0, "scratch was not drained")
        again, current = _load_prepared(root, candidate_sha256)
        _require(again == descriptor and current == manifests, "candidate or manifest changed before proof seal")
        _require(
            seal_code_identity(root, SOURCE_COMMIT, bind_runtime=True, executing=runtime_sources) == code,
            "runtime source or code identity changed before proof seal",
        )
        for manifest in manifests:
            for spec in manifest.files:
                snapshot = _snapshot(root, spec.relative_path)
                _require((snapshot.sha256, snapshot.byte_size) == (spec.sha256, spec.bytes), "reference changed before proof seal")
        _require(_sha(executing.read_bytes()) == checker_source_sha256, "checker source changed before proof seal")
        _require(_scratch_bytes(scratch) == 0, "scratch not empty before seal")
        _require(charged + length + SCRATCH_CAP_BYTES + PUBLICATION_ALLOWANCE_BYTES <= RELEASE_METADATA_REMAINDER_BYTES,
                 "actual proof exceeds release remainder")
        _reserve(root, length + PUBLICATION_ALLOWANCE_BYTES + subtotals["sqlite_bytes"])
        patched = True
        stream.seek(status_offset)
        _require(stream.write(b"PASS") == 4, "proof status patch was incomplete")
        stream.flush()
        os.fsync(stream.fileno())
        final_sha, final_size, _inode, _device = _hash_file(stage)
        _require(final_size == length, "proof length changed after PASS seal")
        final = _seal_proof(stage, final_sha, length, writer_fd=stream.fileno())
    except BaseException:
        try:
            if patched and status_offset is not None:
                stream.seek(status_offset)
                _require(stream.write(b"HOLD") == 4, "failed proof status rollback was incomplete")
                stream.flush()
                os.fsync(stream.fileno())
            if final_sha is not None:
                _restore_failed_stage(stage, final_sha, writer_identity)
        finally:
            stream.close()
        raise
    try:
        stream.close()
    except OSError:
        # The proof file and its directory were already fsynced and renamed.
        pass
    try:
        _progress("PASS", completed_files, completed_rows, began, proof_path=str(final),
                  proof_sha256=final_sha, proof_bytes=length,
                  nautilus_version=NAUTILUS_VERSION, bundle_bytes=bundle_bytes,
                  metadata_charge_bytes=charged + length, sqlite_bytes=subtotals["sqlite_bytes"],
                  scratch_bytes=0)
    except OSError:
        # A sealed proof remains successful if stderr becomes unavailable.
        pass
    assert final_sha is not None
    return final, final_sha


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check_cex002_nautilus_consumer")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--checker-sha", required=True)
    parser.add_argument("--scratch-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        check_release(args.repo, args.candidate_sha, args.checker_sha, args.scratch_root)
    except Exception as exc:
        sys.stderr.write(_json({"stage": "FAILED", "error": str(exc), "error_type": type(exc).__name__}) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
