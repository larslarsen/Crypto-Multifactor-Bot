"""Concrete Gate-3 normalizer for Binance USD-M perpetual membership."""

from __future__ import annotations

import ctypes
import errno
import fcntl
import hashlib
import json
import os
import stat
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    ACCEPTED_DETAILED_MEMBERSHIP_IDENTITIES,
    ACCEPTED_FUNDING_ONLY_MEMBERSHIP_IDENTITIES,
    ACCEPTED_MEMBERSHIP_CLASSIFICATIONS,
    ACCEPTED_MEMBERSHIP_IDENTITIES,
    ACCEPTED_REJECTED_MEMBERSHIP_ROWS,
    FUNDING_ONLY_EVIDENCE_CLASS,
    FUNDING_ONLY_SEMANTICS,
    MEMBERSHIP_ACCEPTED_CLASS,
    MEMBERSHIP_DETAILED_STATE,
    MEMBERSHIP_FUNDING_ONLY_STATE,
    PARQUET_COMPRESSION,
    PARQUET_COMPRESSION_LEVEL,
    PARQUET_VERSION,
    PRODUCT_MEMBERSHIP,
    SIZING_ROW_BATCH,
    final_product_schema,
    native_identity,
    product_schema_identity,
    writer_identity,
)

PRODUCT = PRODUCT_MEMBERSHIP
SCHEMA = final_product_schema(PRODUCT)
SCHEMA_SHA256 = product_schema_identity(PRODUCT)
REPORT_SHA256 = "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
METADATA_SHA256 = "7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42"
SIZING_SHA256 = "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589"
SIZING_POLICY_IDENTITY = "adr0027_review257_partition_aware_dictionary_storage_sizing_v3"
EXPECTED_PROJECTED_BYTES = 5_383_893
MAX_REPORT_BYTES = 16 * 2**20
MAX_METADATA_BYTES = 16 * 2**20
MAX_SIZING_BYTES = 48 * 2**20
RENAME_NOREPLACE = 1

_HEX = frozenset("0123456789abcdef")
_STABLE_FIELDS = (
    "contract_type",
    "status",
    "underlying_type",
    "base_asset",
    "quote_asset",
    "margin_asset",
    "pair",
    "onboard_ms",
    "delivery_ms",
    "closed_observed_ms",
    "semantics_state",
)
_FUNDING_NULL_FIELDS = (
    "contract_status",
    "underlying_type",
    "base_asset",
    "quote_asset",
    "margin_asset",
    "pair",
    "onboard_ms",
    "delivery_ms",
    "closed_observed_ms",
    "contract_snapshot_sha256",
)


class MembershipNormalizationError(RuntimeError):
    """Fail-closed membership authority, typing, or publication error."""


@dataclass(frozen=True, slots=True)
class MembershipAuthority:
    report: Mapping[str, Any]
    metadata: Mapping[str, Any]
    sizing: Mapping[str, Any]
    report_sha256: str
    metadata_sha256: str
    sizing_sha256: str


@dataclass(frozen=True, slots=True)
class PublishedMembershipPartition:
    native_symbol: str
    parquet_path: Path
    parquet_sha256: str
    lineage_path: Path
    lineage_sha256: str
    reused: bool


@dataclass(frozen=True, slots=True)
class MembershipNormalizationResult:
    schema_sha256: str
    partitions: tuple[PublishedMembershipPartition, ...]
    completion_path: Path
    completion_sha256: str
    completion_reused: bool


@dataclass(frozen=True, slots=True)
class PublicationHooks:
    """Test-only interruption boundary; production callers leave it unset."""

    before_publish: Callable[[str, Path, Path], None] | None = None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MembershipNormalizationError(message)


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _is_digest(value: object) -> bool:
    return type(value) is str and len(value) == 64 and not (set(value) - _HEX)


def _schema_contract() -> list[dict[str, Any]]:
    return [
        {"name": field.name, "arrow_type": str(field.type), "nullable": field.nullable}
        for field in SCHEMA
    ]


def _safe_component(value: str) -> str:
    _require(
        type(value) is str
        and bool(value)
        and value not in {".", ".."}
        and "/" not in value
        and "\\" not in value
        and "\x00" not in value,
        "native symbol is not a safe output component",
    )
    return value


def _require_no_symlink_components(path: Path, *, label: str) -> None:
    absolute = path.absolute()
    for component in reversed((absolute, *absolute.parents)):
        if not component.exists() and not component.is_symlink():
            continue
        try:
            facts = component.lstat()
        except OSError as exc:
            raise MembershipNormalizationError(f"{label} cannot be inspected safely") from exc
        _require(not stat.S_ISLNK(facts.st_mode), f"{label} contains a symlink")


def _digest_fd(descriptor: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    position = os.lseek(descriptor, 0, os.SEEK_CUR)
    os.lseek(descriptor, 0, os.SEEK_SET)
    try:
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
            size += len(block)
    finally:
        os.lseek(descriptor, position, os.SEEK_SET)
    return digest.hexdigest(), size


def _read_fd(descriptor: int, maximum: int) -> bytes:
    facts = os.fstat(descriptor)
    _require(stat.S_ISREG(facts.st_mode), "authority is not a regular file")
    _require(0 < facts.st_size <= maximum, "authority exceeds its fixed read bound")
    body = bytearray()
    while block := os.read(descriptor, min(1024 * 1024, maximum + 1 - len(body))):
        body.extend(block)
        _require(len(body) <= maximum, "authority exceeds its fixed read bound")
    return bytes(body)


def _read_pinned_json(path: Path, expected_sha256: str, maximum: int) -> Mapping[str, Any]:
    _require_no_symlink_components(path, label="membership authority path")
    parent = path.absolute().parent
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    descriptor: int | None = None
    try:
        try:
            descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
        except OSError as exc:
            raise MembershipNormalizationError("membership authority cannot be opened no-follow") from exc
        body = _read_fd(descriptor, maximum)
        _require(hashlib.sha256(body).hexdigest() == expected_sha256, "membership authority digest changed")
        try:
            document = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MembershipNormalizationError("membership authority is not valid JSON") from exc
        _require(type(document) is dict, "membership authority is not an object")
        return document
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_fd)


def load_authorities(report_path: Path, metadata_path: Path, sizing_path: Path) -> MembershipAuthority:
    """Read the three exact accepted authorities without following symlinks."""
    return MembershipAuthority(
        report=_read_pinned_json(report_path, REPORT_SHA256, MAX_REPORT_BYTES),
        metadata=_read_pinned_json(metadata_path, METADATA_SHA256, MAX_METADATA_BYTES),
        sizing=_read_pinned_json(sizing_path, SIZING_SHA256, MAX_SIZING_BYTES),
        report_sha256=REPORT_SHA256,
        metadata_sha256=METADATA_SHA256,
        sizing_sha256=SIZING_SHA256,
    )


def _strict_bool(value: object, label: str) -> bool:
    _require(type(value) is bool, f"{label} is not boolean")
    return value


def _optional_int(value: object, label: str) -> int | None:
    if value is None:
        return None
    _require(type(value) is int, f"{label} is not an exact integer")
    return value


def _resolved_evidence(classification: Mapping[str, Any]) -> tuple[dict[str, Any], list[Mapping[str, Any]]]:
    evidence = classification.get("evidence")
    _require(type(evidence) is list and bool(evidence), "accepted membership has no evidence")
    _require(all(type(item) is dict for item in evidence), "membership evidence is not an object")
    records = list(evidence)
    symbol = classification["symbol"]
    for record in records:
        _require(record.get("symbol", symbol) == symbol, "membership evidence names another symbol")
    resolved: dict[str, Any] = {}
    for field in _STABLE_FIELDS:
        values = [record[field] for record in records if record.get(field) not in (None, "")]
        if not values:
            resolved[field] = None
        else:
            _require(all(candidate == values[0] for candidate in values), "membership evidence conflicts on a stable fact")
            resolved[field] = values[0]
    return resolved, records


def _detailed_row(
    classification: Mapping[str, Any],
    resolved: Mapping[str, Any],
    records: list[Mapping[str, Any]],
    symbol_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    symbol = classification["symbol"]
    required = ("contract_type", "status", "underlying_type", "base_asset", "quote_asset", "margin_asset", "pair", "semantics_state")
    _require(all(resolved.get(field) not in (None, "") for field in required), "detailed membership evidence omits contract terms")
    _require(resolved["contract_type"] == "PERPETUAL", "accepted contract is not perpetual")
    _require(resolved["semantics_state"] == "supported", "detailed membership semantics are not supported")
    classes = {record.get("kind") for record in records}
    sources = {record.get("endpoint") for record in records}
    digests = {record.get("response_sha256") for record in records}
    _require(len(classes) == 1 and None not in classes and "" not in classes, "detailed evidence class is ambiguous")
    _require(len(sources) == 1 and None not in sources and "" not in sources, "detailed evidence source is ambiguous")
    _require(len(digests) == 1 and all(_is_digest(item) for item in digests), "detailed evidence digest is ambiguous")
    snapshot = symbol_snapshot.get(symbol)
    _require(_is_digest(snapshot), "detailed membership has no contract snapshot")
    return {
        **native_identity(symbol),
        "membership_class": MEMBERSHIP_ACCEPTED_CLASS,
        "contract_type": "PERPETUAL",
        "contract_metadata_state": MEMBERSHIP_DETAILED_STATE,
        "contract_evidence_class": next(iter(classes)),
        "contract_evidence_source": next(iter(sources)),
        "contract_status": resolved["status"],
        "underlying_type": resolved["underlying_type"],
        "base_asset": resolved["base_asset"],
        "quote_asset": resolved["quote_asset"],
        "margin_asset": resolved["margin_asset"],
        "pair": resolved["pair"],
        "in_archive": _strict_bool(classification.get("in_archive"), "in_archive"),
        "in_current_exchange": _strict_bool(classification.get("in_current_exchange"), "in_current_exchange"),
        "onboard_ms": _optional_int(resolved["onboard_ms"], "onboard_ms"),
        "delivery_ms": _optional_int(resolved["delivery_ms"], "delivery_ms"),
        "closed_observed_ms": _optional_int(resolved["closed_observed_ms"], "closed_observed_ms"),
        "semantics_state": "supported",
        "contract_snapshot_sha256": snapshot,
        "evidence_records": len(records),
    }


def _funding_row(
    classification: Mapping[str, Any],
    resolved: Mapping[str, Any],
    records: list[Mapping[str, Any]],
    symbol_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    symbol = classification["symbol"]
    _require(symbol not in symbol_snapshot, "funding-only membership unexpectedly has ticker metadata")
    _require(all(resolved.get(field) in (None, "") for field in _STABLE_FIELDS), "funding-only evidence carries unavailable ticker terms")
    for record in records:
        _require(record.get("kind") == FUNDING_ONLY_EVIDENCE_CLASS, "funding-only evidence class changed")
        _require(record.get("semantics") == FUNDING_ONLY_SEMANTICS, "funding-only semantics changed")
        families = record.get("families")
        _require(type(families) is list and "monthly/fundingRate" in families, "funding-only evidence lacks realized funding")
        _require(type(record.get("example_key")) is str and bool(record["example_key"]), "funding-only evidence source is missing")
    sources = {record["example_key"] for record in records}
    _require(len(sources) == 1, "funding-only evidence source is ambiguous")
    row = {
        **native_identity(symbol),
        "membership_class": MEMBERSHIP_ACCEPTED_CLASS,
        "contract_type": "PERPETUAL",
        "contract_metadata_state": MEMBERSHIP_FUNDING_ONLY_STATE,
        "contract_evidence_class": FUNDING_ONLY_EVIDENCE_CLASS,
        "contract_evidence_source": next(iter(sources)),
        "contract_status": None,
        "underlying_type": None,
        "base_asset": None,
        "quote_asset": None,
        "margin_asset": None,
        "pair": None,
        "in_archive": _strict_bool(classification.get("in_archive"), "in_archive"),
        "in_current_exchange": _strict_bool(classification.get("in_current_exchange"), "in_current_exchange"),
        "onboard_ms": None,
        "delivery_ms": None,
        "closed_observed_ms": None,
        "semantics_state": FUNDING_ONLY_SEMANTICS,
        "contract_snapshot_sha256": None,
        "evidence_records": len(records),
    }
    _require(all(row[field] is None for field in _FUNDING_NULL_FIELDS), "funding-only null semantics changed")
    return row


def _validate_sizing(sizing: Mapping[str, Any], report_sha: str, metadata_sha: str) -> None:
    authority = sizing.get("authority")
    code = sizing.get("code_identity")
    projections = sizing.get("projections")
    _require(type(authority) is dict and type(code) is dict and type(projections) is dict, "sizing authority shape changed")
    bindings = authority.get("bindings")
    _require(type(bindings) is dict, "sizing authority bindings are missing")
    _require(bindings.get("report_sha256") == report_sha, "sizing report binding changed")
    _require(bindings.get("contract_metadata_sha256") == metadata_sha, "sizing metadata binding changed")
    _require(code.get("policy_identity") == SIZING_POLICY_IDENTITY, "sizing policy changed")
    _require(code.get("writer_identity") == writer_identity(), "sizing writer identity changed")
    schemas = projections.get("final_product_schemas")
    _require(type(schemas) is dict and schemas.get(PRODUCT) == _schema_contract(), "accepted membership schema changed")
    fixed = projections.get("fixed_schema_products")
    _require(type(fixed) is dict and type(fixed.get(PRODUCT)) is dict, "membership sizing projection is missing")
    projection = fixed[PRODUCT]
    _require(projection.get("projected_rows") == ACCEPTED_MEMBERSHIP_IDENTITIES, "membership projected rows changed")
    _require(projection.get("partition_count") == ACCEPTED_MEMBERSHIP_IDENTITIES, "membership projected partitions changed")
    _require(projection.get("projected_bytes") == EXPECTED_PROJECTED_BYTES, "membership projected bytes changed")


def build_membership_rows(
    report: Mapping[str, Any], metadata: Mapping[str, Any], *, enforce_full_corpus: bool,
) -> tuple[tuple[dict[str, Any], ...], tuple[Mapping[str, Any], ...]]:
    """Validate classifications and construct only confirmed-perpetual rows."""
    membership = report.get("membership")
    _require(type(membership) is dict, "report membership authority is missing")
    _require(membership.get("resolved") is True, "membership authority is unresolved")
    _require(membership.get("unresolved_count") == 0 and membership.get("unresolved_symbols") == [], "membership authority has unresolved identities")
    classifications = membership.get("classifications")
    _require(type(classifications) is list and bool(classifications), "membership classifications are missing")
    symbol_snapshot = metadata.get("symbol_snapshot")
    _require(type(symbol_snapshot) is dict, "contract metadata symbol map is missing")
    rows: list[dict[str, Any]] = []
    exclusions: list[Mapping[str, Any]] = []
    symbols: set[str] = set()
    for item in classifications:
        _require(type(item) is dict, "membership classification is not an object")
        symbol = item.get("symbol")
        _safe_component(symbol)
        _require(symbol not in symbols, "membership classification repeats a symbol")
        symbols.add(symbol)
        accepted = _strict_bool(item.get("accepted"), "accepted")
        blocking = _strict_bool(item.get("blocking"), "blocking")
        membership_class = item.get("membership_class")
        if not accepted:
            _require(membership_class != MEMBERSHIP_ACCEPTED_CLASS, "confirmed perpetual was excluded")
            exclusions.append(item)
            continue
        _require(not blocking, "accepted membership is blocking")
        _require(membership_class == MEMBERSHIP_ACCEPTED_CLASS, "accepted membership class changed")
        resolved, evidence = _resolved_evidence(item)
        detailed = any(resolved.get(field) not in (None, "") for field in _STABLE_FIELDS)
        row = (
            _detailed_row(item, resolved, evidence, symbol_snapshot)
            if detailed
            else _funding_row(item, resolved, evidence, symbol_snapshot)
        )
        _require(pa.Table.from_pylist([row], schema=SCHEMA).schema == SCHEMA, "membership row deviates from typed schema")
        rows.append(row)
    rows.sort(key=lambda row: row["native_symbol"])
    exclusions.sort(key=lambda row: str(row["symbol"]))
    detailed_count = sum(row["contract_metadata_state"] == MEMBERSHIP_DETAILED_STATE for row in rows)
    funding_count = sum(row["contract_metadata_state"] == MEMBERSHIP_FUNDING_ONLY_STATE for row in rows)
    if enforce_full_corpus:
        _require(len(classifications) == ACCEPTED_MEMBERSHIP_CLASSIFICATIONS, "classification count changed")
        _require(len(rows) == ACCEPTED_MEMBERSHIP_IDENTITIES, "accepted membership count changed")
        _require(len(exclusions) == ACCEPTED_REJECTED_MEMBERSHIP_ROWS, "membership exclusion count changed")
        _require(membership.get("confirmed_count") == ACCEPTED_MEMBERSHIP_IDENTITIES, "confirmed membership count changed")
        _require(detailed_count == ACCEPTED_DETAILED_MEMBERSHIP_IDENTITIES, "detailed membership count changed")
        _require(funding_count == ACCEPTED_FUNDING_ONLY_MEMBERSHIP_IDENTITIES, "funding-only membership count changed")
    _require(detailed_count + funding_count == len(rows), "membership evidence classes do not partition rows")
    return tuple(rows), tuple(exclusions)


def _rewrite_fd(descriptor: int, body: bytes) -> None:
    os.ftruncate(descriptor, 0)
    os.lseek(descriptor, 0, os.SEEK_SET)
    view = memoryview(body)
    while view:
        written = os.write(descriptor, view)
        _require(written > 0, "staged output write was incomplete")
        view = view[written:]
    os.fsync(descriptor)


def _same_fds(left: int, right: int) -> bool:
    left_position = os.lseek(left, 0, os.SEEK_CUR)
    right_position = os.lseek(right, 0, os.SEEK_CUR)
    os.lseek(left, 0, os.SEEK_SET)
    os.lseek(right, 0, os.SEEK_SET)
    try:
        while block := os.read(left, 1024 * 1024):
            if block != os.read(right, len(block)):
                return False
        return os.read(right, 1) == b""
    finally:
        os.lseek(left, left_position, os.SEEK_SET)
        os.lseek(right, right_position, os.SEEK_SET)


def _rename_noreplace_at(old_dir: int, old_name: str, new_dir: int, new_name: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = libc.renameat2
    except AttributeError as exc:
        raise MembershipNormalizationError("atomic no-replace rename is unavailable") from exc
    renameat2.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    renameat2.restype = ctypes.c_int
    if renameat2(old_dir, os.fsencode(old_name), new_dir, os.fsencode(new_name), RENAME_NOREPLACE):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), new_name)


class _OutputTree:
    def __init__(self, root: Path) -> None:
        _require(root.name.startswith("."), "membership output root must be hidden")
        _require_no_symlink_components(root, label="membership output root")
        if not root.exists():
            root.mkdir(mode=0o700)
            parent_fd = os.open(root.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        self.root = root.resolve(strict=True)
        self.root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            fcntl.flock(self.root_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.root_fd)
            raise MembershipNormalizationError("another normalizer holds the membership root") from exc
        self.root_facts = os.fstat(self.root_fd)
        os.close(self.directory((".staging",), create=True))

    def close(self) -> None:
        os.close(self.root_fd)

    def directory(self, parts: Sequence[str], *, create: bool) -> int:
        current = os.dup(self.root_fd)
        try:
            for raw in parts:
                name = _safe_component(raw)
                if create:
                    try:
                        os.mkdir(name, 0o700, dir_fd=current)
                        os.fsync(current)
                    except FileExistsError:
                        pass
                try:
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
                except OSError as exc:
                    raise MembershipNormalizationError("membership output directory is unsafe") from exc
                os.close(current)
                current = child
            return current
        except Exception:
            os.close(current)
            raise

    def stage(self, prefix: str) -> tuple[str, int]:
        directory = self.directory((".staging",), create=False)
        name = f"{_safe_component(prefix)}-{uuid.uuid4().hex}.tmp"
        try:
            descriptor = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=directory)
        finally:
            os.close(directory)
        return name, descriptor

    def publish(self, stage_name: str, stage_fd: int, parts: Sequence[str], name: str, *, kind: str, hooks: PublicationHooks) -> tuple[bool, int, Path]:
        staging = self.directory((".staging",), create=False)
        destination = self.directory(parts, create=True)
        path = self.root.joinpath(*parts, name)
        try:
            if hooks.before_publish is not None:
                hooks.before_publish(kind, self.root / ".staging" / stage_name, path)
            try:
                _rename_noreplace_at(staging, stage_name, destination, name)
                os.fsync(destination)
                os.fsync(staging)
                reused = False
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise MembershipNormalizationError("content-addressed membership publication failed") from exc
                winner = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=destination)
                try:
                    _require(stat.S_ISREG(os.fstat(winner).st_mode), "publication winner is not regular")
                    _require(_same_fds(stage_fd, winner), "content-addressed replay differs from existing bytes")
                finally:
                    os.close(winner)
                os.unlink(stage_name, dir_fd=staging)
                os.fsync(staging)
                reused = True
            final_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=destination)
            _require(stat.S_ISREG(os.fstat(final_fd).st_mode), "published membership object is not regular")
            return reused, final_fd, path
        finally:
            os.close(destination)
            os.close(staging)

    def require_only_completion(self, name: str) -> None:
        directory = self.directory((".complete",), create=True)
        try:
            _require(not [entry for entry in os.listdir(directory) if entry != name], "another membership completion already exists")
        finally:
            os.close(directory)

    def verify_paths(self, paths: Iterable[Path]) -> None:
        current = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            facts = os.fstat(current)
            _require((facts.st_dev, facts.st_ino) == (self.root_facts.st_dev, self.root_facts.st_ino), "held membership root was replaced")
        finally:
            os.close(current)
        for path in paths:
            _require(path.is_relative_to(self.root), "published path escapes the held root")
            relative = path.relative_to(self.root)
            directory = self.directory(relative.parts[:-1], create=False)
            try:
                descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
                _require(stat.S_ISREG(os.fstat(descriptor).st_mode), "published membership path is unsafe")
                os.close(descriptor)
            finally:
                os.close(directory)


def _publish_json(tree: _OutputTree, document: Mapping[str, Any], *, parts: Sequence[str], prefix: str, kind: str, hooks: PublicationHooks) -> tuple[Path, str, bool]:
    body = _canonical_json(document)
    digest = hashlib.sha256(body).hexdigest()
    stage_name, stage_fd = tree.stage(prefix)
    final_fd: int | None = None
    try:
        _rewrite_fd(stage_fd, body)
        reused, final_fd, path = tree.publish(stage_name, stage_fd, parts, f"{digest}.json", kind=kind, hooks=hooks)
        actual, size = _digest_fd(final_fd)
        _require(actual == digest and size == len(body), "published membership JSON changed")
        return path, digest, reused
    finally:
        if final_fd is not None:
            os.close(final_fd)
        os.close(stage_fd)


def _publish_partition(tree: _OutputTree, row: Mapping[str, Any], hooks: PublicationHooks) -> tuple[Path, str, bool]:
    symbol = row["native_symbol"]
    table = pa.Table.from_pylist([row], schema=SCHEMA)
    stage_name, stage_fd = tree.stage(f"partition-{symbol}")
    final_fd: int | None = None
    try:
        pq.write_table(
            table,
            f"/proc/self/fd/{stage_fd}",
            compression=PARQUET_COMPRESSION,
            compression_level=PARQUET_COMPRESSION_LEVEL,
            version=PARQUET_VERSION,
            write_statistics=False,
            store_schema=True,
            row_group_size=SIZING_ROW_BATCH,
        )
        os.fsync(stage_fd)
        digest, _size = _digest_fd(stage_fd)
        staged = pq.ParquetFile(f"/proc/self/fd/{stage_fd}")
        _require(staged.schema_arrow == SCHEMA and staged.metadata.num_rows == 1, "staged membership Parquet changed")
        reused, final_fd, path = tree.publish(stage_name, stage_fd, (".partitions", symbol), f"{digest}.parquet", kind="partition", hooks=hooks)
        actual, _size = _digest_fd(final_fd)
        published = pq.ParquetFile(f"/proc/self/fd/{final_fd}")
        _require(actual == digest and published.schema_arrow == SCHEMA and published.metadata.num_rows == 1, "published membership Parquet changed")
        return path, digest, reused
    finally:
        if final_fd is not None:
            os.close(final_fd)
        os.close(stage_fd)


def _source_digest(path: Path) -> str:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        return _digest_fd(descriptor)[0]
    finally:
        os.close(descriptor)


def _normalize(
    authority: MembershipAuthority,
    output_root: Path,
    *,
    enforce_full_corpus: bool,
    hooks: PublicationHooks,
) -> MembershipNormalizationResult:
    _validate_sizing(authority.sizing, authority.report_sha256, authority.metadata_sha256)
    rows, exclusions = build_membership_rows(authority.report, authority.metadata, enforce_full_corpus=enforce_full_corpus)
    tree = _OutputTree(output_root)
    try:
        partitions: list[PublishedMembershipPartition] = []
        for row in rows:
            symbol = row["native_symbol"]
            parquet_path, parquet_sha, parquet_reused = _publish_partition(tree, row, hooks)
            classification = next(item for item in authority.report["membership"]["classifications"] if item["symbol"] == symbol)
            lineage = {
                "document_type": f"{PRODUCT}_partition_lineage",
                "schema_version": 1,
                "required_product": PRODUCT,
                "native_symbol": symbol,
                "row_count": 1,
                "schema_sha256": SCHEMA_SHA256,
                "writer_identity": writer_identity(),
                "parquet_sha256": parquet_sha,
                "parquet_path": str(parquet_path.relative_to(tree.root)),
                "authority_sha256": {
                    "report": authority.report_sha256,
                    "contract_metadata": authority.metadata_sha256,
                    "sizing": authority.sizing_sha256,
                },
                "classification_sha256": hashlib.sha256(_canonical_json(classification)).hexdigest(),
                "contract_snapshot_sha256": row["contract_snapshot_sha256"],
                "evidence_records": row["evidence_records"],
            }
            lineage_path, lineage_sha, lineage_reused = _publish_json(
                tree, lineage, parts=(".lineage", symbol), prefix=f"lineage-{symbol}", kind="lineage", hooks=hooks,
            )
            partitions.append(PublishedMembershipPartition(symbol, parquet_path, parquet_sha, lineage_path, lineage_sha, parquet_reused and lineage_reused))
        exclusion_hasher = hashlib.sha256()
        for exclusion in exclusions:
            exclusion_hasher.update(_canonical_json(exclusion))
        partition_facts = [
            {
                "native_symbol": item.native_symbol,
                "row_count": 1,
                "parquet_sha256": item.parquet_sha256,
                "parquet_path": str(item.parquet_path.relative_to(tree.root)),
                "lineage_sha256": item.lineage_sha256,
                "lineage_path": str(item.lineage_path.relative_to(tree.root)),
            }
            for item in partitions
        ]
        detailed = sum(row["contract_metadata_state"] == MEMBERSHIP_DETAILED_STATE for row in rows)
        funding = len(rows) - detailed
        normalizer_sha = _source_digest(Path(__file__).resolve(strict=True))
        completion = {
            "document_type": f"{PRODUCT}_product_completion",
            "schema_version": 1,
            "required_product": PRODUCT,
            "schema_sha256": SCHEMA_SHA256,
            "writer_identity": writer_identity(),
            "normalizer_source_sha256": normalizer_sha,
            "authorities_authenticated": enforce_full_corpus,
            "authority_sha256": {
                "report": authority.report_sha256,
                "contract_metadata": authority.metadata_sha256,
                "sizing": authority.sizing_sha256,
            },
            "classification_count": len(rows) + len(exclusions),
            "membership_rows": len(rows),
            "excluded_classifications": len(exclusions),
            "detailed_metadata_rows": detailed,
            "funding_only_rows": funding,
            "excluded_classifications_sha256": exclusion_hasher.hexdigest(),
            "row_equation": {
                "classifications": len(rows) + len(exclusions),
                "accepted_membership_rows": len(rows),
                "excluded_classifications": len(exclusions),
            },
            "metadata_equation": {
                "accepted_membership_rows": len(rows),
                "detailed_metadata_rows": detailed,
                "funding_only_rows": funding,
            },
            "partitions": partition_facts,
        }
        expected = hashlib.sha256(_canonical_json(completion)).hexdigest()
        tree.require_only_completion(f"{expected}.json")
        completion_path, completion_sha, completion_reused = _publish_json(
            tree, completion, parts=(".complete",), prefix="membership-completion", kind="completion", hooks=hooks,
        )
        _require(completion_sha == expected, "membership completion identity changed")
        tree.require_only_completion(f"{expected}.json")
        tree.verify_paths(
            [*(item.parquet_path for item in partitions), *(item.lineage_path for item in partitions), completion_path]
        )
        return MembershipNormalizationResult(SCHEMA_SHA256, tuple(partitions), completion_path, completion_sha, completion_reused)
    finally:
        tree.close()


def normalize_membership_documents(
    report: Mapping[str, Any],
    metadata: Mapping[str, Any],
    sizing: Mapping[str, Any],
    output_root: Path,
    *,
    report_sha256: str = REPORT_SHA256,
    metadata_sha256: str = METADATA_SHA256,
    sizing_sha256: str = SIZING_SHA256,
    hooks: PublicationHooks = PublicationHooks(),
) -> MembershipNormalizationResult:
    """Normalize authenticated-shaped documents for bounded focused tests."""
    return _normalize(
        MembershipAuthority(report, metadata, sizing, report_sha256, metadata_sha256, sizing_sha256),
        output_root,
        enforce_full_corpus=False,
        hooks=hooks,
    )


def normalize_from_authorities(
    *,
    report_path: Path,
    contract_metadata_path: Path,
    sizing_path: Path,
    output_root: Path,
    hooks: PublicationHooks = PublicationHooks(),
) -> MembershipNormalizationResult:
    """Publish the exact accepted 771-row membership authority."""
    authority = load_authorities(report_path, contract_metadata_path, sizing_path)
    return _normalize(authority, output_root, enforce_full_corpus=True, hooks=hooks)
