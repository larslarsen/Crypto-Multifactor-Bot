"""Renewable capacity attestation over the immutable CEX-002 v3 sizing basis."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

RECEIPT_RELATIVE_PATH = Path(
    "research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json"
)
ATTESTATION_ROOT = Path("research/sprint_004")
SOURCE_RELATIVE_PATH = Path(
    "src/cryptofactors/acquisition/binance_usdm_capacity_attestation.py"
)
CLI_RELATIVE_PATH = Path(
    "scripts/research/attest_binance_usdm_harmonic_capacity.py"
)

EXPECTED_RECEIPT_SHA256 = (
    "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589"
)
EXPECTED_RECEIPT_BYTES = 39_727_059
EXPECTED_RECEIPT_SCHEMA = "cex002_gate2_storage_sizing_v3"
EXPECTED_RECEIPT_POLICY = (
    "adr0027_review257_partition_aware_dictionary_storage_sizing_v3"
)
EXPECTED_SIZING_SOURCE_SHA256 = (
    "d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b"
)
EXPECTED_SIZING_CLI_SHA256 = (
    "36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c"
)
EXPECTED_DESTINATION = "data/cex002_qualify"
EXPECTED_DEVICE = "dev:64513"
EXPECTED_RESERVE_RULE = "max(16 GiB, ceil(pre_write_available / 5)), never lowered"
EXPECTED_CAPACITY_EQUATION = (
    "new Binance raw + new Coinalyze raw + typed normalized partitions + "
    "catalog/manifest/bundle + bounded temporary work + operating reserve, counted "
    "once and without overlap"
)
EXPECTED_AUTHORIZATION = (
    "a sufficient storage preflight is a measurement only: it accepts no gate, "
    "authorizes no acquisition, and changes no ticket state"
)
STABLE_COMPONENTS = {
    "new_binance_raw_bytes": 20_351_715_427,
    "new_coinalyze_raw_bytes": 30_580_702,
    "typed_normalized_partition_bytes": 108_082_947_883,
    "catalog_manifest_bundle_bytes": 5_556_368_003,
    "bounded_temporary_work_bytes": 5_556_368_003,
}
EXPECTED_STABLE_REQUIREMENT_BYTES = 139_577_980_018
MINIMUM_OPERATING_RESERVE_BYTES = 16 * 2**30
RESERVE_DIVISOR = 5
ATTESTATION_SCHEMA = "cex002_gate2_capacity_attestation_v1"
ATTESTATION_POLICY = "adr0028_immutable_basis_renewable_capacity_attestation_v1"
BLOCKER_CAPACITY = "available_capacity_insufficient"
STATE_BLOCKED = "blocked"
STATE_SUFFICIENT = "sufficient"
FILESYSTEM_ACCOUNTING = (
    "post-publication availability is the lesser of the same-device measurement after "
    "durable staging and pre-write availability less the attestation's exact canonical "
    "byte length"
)
ATTESTATION_CAPACITY_EQUATION = (
    "accepted_stable_requirement_bytes + current_operating_reserve_bytes = current_total_"
    "requirement_bytes; sufficient iff current total requirement <= post-attestation "
    "available bytes"
)
AUTHORIZATION = {
    "gate_2_accepted": False,
    "acquisition_authorized": False,
    "statement": (
        "this attestation is measurement evidence only; it accepts no gate, authorizes "
        "no acquisition, and changes no ticket state"
    ),
}
SELF_IDENTITY_ALGORITHM = "sha256"
SELF_IDENTITY_SCOPE = "canonical attestation excluding self_identity"
SELF_IDENTITY_CANONICALIZATION = "UTF-8 JSON, indent=2, sorted keys, trailing LF"
RENAME_NOREPLACE = 1
STABLE_RECEIPT_FIELDS = (
    "schema_version",
    "ticket",
    "policy_identity",
    "code_identity",
    "authority",
    "physical_inputs",
    "cohort",
    "typed_schema_contract",
    "lineage",
    "future_width_allocations",
    "coverage_authority",
    "cost_calibration_components",
    "fee_authority",
    "measurements",
    "projections",
    "coinalyze",
    "counts",
    "partitioning",
)
STABLE_CAPACITY_FIELDS = (
    "new_binance_raw_bytes",
    "new_coinalyze_raw_bytes",
    "typed_normalized_partition_bytes",
    "catalog_manifest_bundle_bytes",
    "bounded_temporary_work_bytes",
    "reserve_rule",
    "equation",
)


class AttestationError(RuntimeError):
    """An invalid authority, unsafe publication, or incomplete observation."""

    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = dict(context or {})


@dataclass(frozen=True, slots=True)
class SizingBasis:
    receipt_sha256: str
    receipt_bytes: int
    receipt_schema: str
    receipt_policy: str
    receipt_code_identity: Mapping[str, Any]
    destination: str
    device: str
    receipt_file_device: str
    stable_components: Mapping[str, int]
    stable_requirement_bytes: int
    reserve_rule: str
    capacity_equation: str
    stable_receipt_identity: str


def canonical_json(payload: Mapping[str, Any]) -> bytes:
    """Canonical durable JSON used by the receipt and attestation."""
    return (
        json.dumps(dict(payload), indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def stable_receipt_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Accepted v3 observation-independent boundary, frozen byte-equivalently."""
    capacity = dict(receipt.get("capacity") or {})
    projection: dict[str, Any] = {
        name: receipt.get(name) for name in STABLE_RECEIPT_FIELDS
    }
    projection["capacity"] = {
        name: capacity.get(name) for name in STABLE_CAPACITY_FIELDS
    }
    return json.loads(canonical_json(projection).decode("utf-8"))


def stable_receipt_identity(receipt: Mapping[str, Any]) -> str:
    """SHA-256 of the complete locally frozen stable receipt projection."""
    return hashlib.sha256(canonical_json(stable_receipt_projection(receipt))).hexdigest()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _unique_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _decode_canonical(payload: bytes, *, label: str) -> dict[str, Any]:
    try:
        document = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise AttestationError(f"the {label} is not strict JSON") from exc
    if not isinstance(document, dict) or canonical_json(document) != payload:
        raise AttestationError(f"the {label} is not canonical JSON")
    return document


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AttestationError(message)


def operating_reserve_bytes(pre_write_available_bytes: int) -> int:
    """ADR-0028 reserve derived solely from current pre-write availability."""
    _require(
        isinstance(pre_write_available_bytes, int)
        and not isinstance(pre_write_available_bytes, bool)
        and pre_write_available_bytes > 0,
        "pre-write availability is not a positive integer",
    )
    return max(
        MINIMUM_OPERATING_RESERVE_BYTES,
        (pre_write_available_bytes + RESERVE_DIVISOR - 1) // RESERVE_DIVISOR,
    )


def derive_capacity(
    basis: SizingBasis, *, pre_write_available_bytes: int, post_available_bytes: int
) -> dict[str, Any]:
    """Derive the renewable reserve, total, blocker, and state without overrides."""
    reserve = operating_reserve_bytes(pre_write_available_bytes)
    _require(
        isinstance(post_available_bytes, int)
        and not isinstance(post_available_bytes, bool)
        and post_available_bytes >= 0,
        "post-publication availability is not a nonnegative integer",
    )
    total = basis.stable_requirement_bytes + reserve
    blocked = total > post_available_bytes
    return {
        "stable_requirement_bytes": basis.stable_requirement_bytes,
        "operating_reserve_bytes": reserve,
        "total_future_storage_bytes": total,
        "reserve_rule": basis.reserve_rule,
        "equation": ATTESTATION_CAPACITY_EQUATION,
        "blockers": [BLOCKER_CAPACITY] if blocked else [],
        "storage_preflight_state": STATE_BLOCKED if blocked else STATE_SUFFICIENT,
    }


def _validate_receipt_semantics(
    receipt: Mapping[str, Any], *, receipt_file_device: str
) -> SizingBasis:
    capacity = receipt.get("capacity")
    filesystem = receipt.get("filesystem")
    code_identity = receipt.get("code_identity")
    _require(isinstance(capacity, dict), "receipt 258 has no capacity object")
    _require(isinstance(filesystem, dict), "receipt 258 has no filesystem object")
    _require(isinstance(code_identity, dict), "receipt 258 has no code identity")
    _require(receipt.get("ticket") == "CEX-002", "receipt 258 names another ticket")
    _require(
        receipt.get("schema_version") == EXPECTED_RECEIPT_SCHEMA,
        "receipt 258 has the wrong schema",
    )
    _require(
        code_identity.get("policy_identity") == EXPECTED_RECEIPT_POLICY,
        "receipt 258 has the wrong sizing policy",
    )
    _require(
        code_identity.get("sizing_source_sha256") == EXPECTED_SIZING_SOURCE_SHA256,
        "receipt 258 has the wrong sizing source identity",
    )
    _require(
        code_identity.get("sizing_cli_sha256") == EXPECTED_SIZING_CLI_SHA256,
        "receipt 258 has the wrong sizing CLI identity",
    )
    for name, expected in STABLE_COMPONENTS.items():
        _require(
            capacity.get(name) == expected,
            f"receipt 258 stable component {name} changed",
        )
    stable_sum = sum(STABLE_COMPONENTS.values())
    _require(
        stable_sum == EXPECTED_STABLE_REQUIREMENT_BYTES,
        "the accepted stable capacity sum is inconsistent",
    )
    _require(
        capacity.get("reserve_rule") == EXPECTED_RESERVE_RULE,
        "receipt 258 has the wrong reserve rule",
    )
    _require(
        capacity.get("equation") == EXPECTED_CAPACITY_EQUATION,
        "receipt 258 has the wrong capacity equation",
    )
    _require(
        filesystem.get("destination") == EXPECTED_DESTINATION,
        "receipt 258 has the wrong destination",
    )
    _require(
        filesystem.get("device") == EXPECTED_DEVICE,
        "receipt 258 has the wrong destination device",
    )
    _require(
        receipt_file_device == EXPECTED_DEVICE,
        "receipt 258 is stored on a different device than it declares",
    )
    _require(
        filesystem.get("durable_receipt_bytes") == EXPECTED_RECEIPT_BYTES,
        "receipt 258 has the wrong durable byte count",
    )
    pre = filesystem.get("pre_write_available_bytes")
    post = filesystem.get("post_publication_available_bytes")
    _require(isinstance(pre, int) and pre > 0, "receipt 258 pre-write capacity is invalid")
    _require(isinstance(post, int) and post >= 0, "receipt 258 post capacity is invalid")
    reserve = operating_reserve_bytes(pre)
    _require(
        capacity.get("operating_reserve_bytes") == reserve,
        "receipt 258 reserve does not follow its rule",
    )
    total = stable_sum + reserve
    _require(
        capacity.get("total_future_storage_bytes") == total,
        "receipt 258 total does not reconcile",
    )
    _require(total > post, "receipt 258 is not internally blocked")
    _require(
        receipt.get("blockers") == [BLOCKER_CAPACITY],
        "receipt 258 blockers are not internally whole",
    )
    _require(
        receipt.get("storage_preflight_state") == STATE_BLOCKED,
        "receipt 258 state is not internally blocked",
    )
    _require(
        receipt.get("authorization") == EXPECTED_AUTHORIZATION,
        "receipt 258 has the wrong authorization boundary",
    )
    full_stable_identity = stable_receipt_identity(receipt)
    return SizingBasis(
        receipt_sha256=EXPECTED_RECEIPT_SHA256,
        receipt_bytes=EXPECTED_RECEIPT_BYTES,
        receipt_schema=EXPECTED_RECEIPT_SCHEMA,
        receipt_policy=EXPECTED_RECEIPT_POLICY,
        receipt_code_identity=dict(code_identity),
        destination=EXPECTED_DESTINATION,
        device=EXPECTED_DEVICE,
        receipt_file_device=receipt_file_device,
        stable_components=dict(STABLE_COMPONENTS),
        stable_requirement_bytes=stable_sum,
        reserve_rule=EXPECTED_RESERVE_RULE,
        capacity_equation=EXPECTED_CAPACITY_EQUATION,
        stable_receipt_identity=full_stable_identity,
    )


def validate_receipt_bytes(payload: bytes, *, receipt_file_device: str) -> SizingBasis:
    """Bind exact receipt bytes, then independently prove every stable boundary."""
    _require(len(payload) == EXPECTED_RECEIPT_BYTES, "receipt 258 length changed")
    _require(_sha256(payload) == EXPECTED_RECEIPT_SHA256, "receipt 258 hash changed")
    receipt = _decode_canonical(payload, label="receipt 258")
    return _validate_receipt_semantics(
        receipt, receipt_file_device=receipt_file_device
    )


def _validate_parts(parts: Sequence[str], *, label: str) -> None:
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise AttestationError(f"the {label} path is not a safe relative path")


def _open_directory_chain(root: Path, parts: Sequence[str], *, label: str) -> int:
    _validate_parts(parts, label=label)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current = os.open(str(root), flags)
        for part in parts:
            try:
                following = os.open(part, flags, dir_fd=current)
            finally:
                os.close(current)
            current = following
        return current
    except OSError as exc:
        raise AttestationError(f"the {label} path is not a no-follow directory") from exc


def _read_repository_file_with_device(
    repository: Path, relative: Path, *, label: str
) -> tuple[bytes, str]:
    _validate_parts(relative.parts, label=label)
    directory = _open_directory_chain(repository, relative.parent.parts, label=label)
    try:
        try:
            handle = os.open(
                relative.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory
            )
        except OSError as exc:
            raise AttestationError(f"the {label} is not a no-follow regular file") from exc
        try:
            metadata = os.fstat(handle)
            mode = metadata.st_mode
            _require(stat.S_ISREG(mode), f"the {label} is not a regular file")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(handle, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks), f"dev:{metadata.st_dev}"
        finally:
            os.close(handle)
    finally:
        os.close(directory)


def _read_repository_file(repository: Path, relative: Path, *, label: str) -> bytes:
    payload, _device_identity = _read_repository_file_with_device(
        repository, relative, label=label
    )
    return payload


def load_accepted_basis(repository: Path) -> SizingBasis:
    payload, receipt_file_device = _read_repository_file_with_device(
        repository, RECEIPT_RELATIVE_PATH, label="receipt 258"
    )
    return validate_receipt_bytes(
        payload, receipt_file_device=receipt_file_device
    )


def attestation_code_identity(repository: Path) -> dict[str, str]:
    source = _read_repository_file(
        repository, SOURCE_RELATIVE_PATH, label="attestation source"
    )
    cli = _read_repository_file(repository, CLI_RELATIVE_PATH, label="attestation CLI")
    return {
        "policy_identity": ATTESTATION_POLICY,
        "attestation_source_sha256": _sha256(source),
        "attestation_cli_sha256": _sha256(cli),
        "attestation_source_path": str(SOURCE_RELATIVE_PATH),
        "attestation_cli_path": str(CLI_RELATIVE_PATH),
    }


def _basis_document(basis: SizingBasis) -> dict[str, Any]:
    return {
        "receipt_relative_path": str(RECEIPT_RELATIVE_PATH),
        "receipt_sha256": basis.receipt_sha256,
        "receipt_bytes": basis.receipt_bytes,
        "receipt_schema_version": basis.receipt_schema,
        "receipt_policy_identity": basis.receipt_policy,
        "receipt_code_identity": dict(basis.receipt_code_identity),
        "destination": basis.destination,
        "device": basis.device,
        "receipt_file_device": basis.receipt_file_device,
        "stable_capacity_components": dict(basis.stable_components),
        "stable_requirement_bytes": basis.stable_requirement_bytes,
        "stable_receipt_identity": basis.stable_receipt_identity,
        "reserve_rule": basis.reserve_rule,
        "capacity_equation": basis.capacity_equation,
    }


def render_attestation(
    basis: SizingBasis,
    *,
    code_identity: Mapping[str, str],
    generated_at: str,
    pre_write_available_bytes: int,
    measured_after_staging_available_bytes: int,
) -> tuple[dict[str, Any], bytes]:
    """Render a canonical document whose durable byte count is self-consistent."""
    _require(bool(generated_at), "the measurement time is empty")
    _require(
        isinstance(measured_after_staging_available_bytes, int)
        and measured_after_staging_available_bytes >= 0,
        "the after-staging capacity is not a nonnegative integer",
    )
    durable_bytes = 0
    for _ in range(16):
        post = min(
            measured_after_staging_available_bytes,
            max(pre_write_available_bytes - durable_bytes, 0),
        )
        capacity = derive_capacity(
            basis,
            pre_write_available_bytes=pre_write_available_bytes,
            post_available_bytes=post,
        )
        document: dict[str, Any] = {
            "schema_version": ATTESTATION_SCHEMA,
            "ticket": "CEX-002",
            "generated_at": generated_at,
            "basis": _basis_document(basis),
            "code_identity": dict(code_identity),
            "filesystem": {
                "destination": basis.destination,
                "device": basis.device,
                "pre_write_available_bytes": pre_write_available_bytes,
                "measured_after_staging_available_bytes": (
                    measured_after_staging_available_bytes
                ),
                "durable_attestation_bytes": durable_bytes,
                "post_publication_available_bytes": post,
                "accounting": FILESYSTEM_ACCOUNTING,
            },
            "capacity": {
                key: value
                for key, value in capacity.items()
                if key not in {"blockers", "storage_preflight_state"}
            },
            "blockers": capacity["blockers"],
            "storage_preflight_state": capacity["storage_preflight_state"],
            "authorization": dict(AUTHORIZATION),
        }
        identity_payload = canonical_json(document)
        document["self_identity"] = {
            "algorithm": SELF_IDENTITY_ALGORITHM,
            "scope": SELF_IDENTITY_SCOPE,
            "payload_sha256": _sha256(identity_payload),
            "canonicalization": SELF_IDENTITY_CANONICALIZATION,
        }
        body = canonical_json(document)
        if len(body) == durable_bytes:
            return document, body
        durable_bytes = len(body)
    raise AttestationError("the attestation self-length did not converge")


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], *, label: str
) -> None:
    _require(set(value) == expected, f"the attestation {label} shape is not closed")


def _require_utc_timestamp(value: Any) -> None:
    _require(isinstance(value, str) and bool(value), "the measurement time is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise AttestationError("the measurement time is invalid") from exc
    _require(
        parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0),
        "the measurement time is not UTC",
    )


def validate_attestation_bytes(
    payload: bytes,
    *,
    basis: SizingBasis,
    code_identity: Mapping[str, str],
) -> dict[str, Any]:
    """Reauthenticate the complete closed attestation against current code and basis."""
    document = _decode_canonical(payload, label="capacity attestation")
    _require_exact_keys(
        document,
        {
            "schema_version",
            "ticket",
            "generated_at",
            "basis",
            "code_identity",
            "filesystem",
            "capacity",
            "blockers",
            "storage_preflight_state",
            "authorization",
            "self_identity",
        },
        label="top-level",
    )
    _require(
        document["schema_version"] == ATTESTATION_SCHEMA,
        "the attestation has the wrong schema",
    )
    _require(document["ticket"] == "CEX-002", "the attestation names another ticket")
    _require_utc_timestamp(document["generated_at"])
    _require(
        document["basis"] == _basis_document(basis),
        "the attestation basis does not match receipt 258",
    )
    _require(
        document["code_identity"] == dict(code_identity),
        "the attestation code identity does not match current source",
    )
    filesystem = document["filesystem"]
    capacity = document["capacity"]
    identity = document["self_identity"]
    authorization = document["authorization"]
    _require(isinstance(filesystem, dict), "the attestation has no filesystem object")
    _require(isinstance(capacity, dict), "the attestation has no capacity object")
    _require(isinstance(identity, dict), "the attestation has no self identity")
    _require(isinstance(authorization, dict), "the attestation has no authorization")
    _require_exact_keys(
        filesystem,
        {
            "destination",
            "device",
            "pre_write_available_bytes",
            "measured_after_staging_available_bytes",
            "durable_attestation_bytes",
            "post_publication_available_bytes",
            "accounting",
        },
        label="filesystem",
    )
    _require_exact_keys(
        capacity,
        {
            "stable_requirement_bytes",
            "operating_reserve_bytes",
            "total_future_storage_bytes",
            "reserve_rule",
            "equation",
        },
        label="capacity",
    )
    _require_exact_keys(
        authorization,
        {"gate_2_accepted", "acquisition_authorized", "statement"},
        label="authorization",
    )
    _require_exact_keys(
        identity,
        {"algorithm", "scope", "payload_sha256", "canonicalization"},
        label="self identity",
    )
    _require(
        filesystem["destination"] == basis.destination
        and filesystem["device"] == basis.device
        and filesystem["accounting"] == FILESYSTEM_ACCOUNTING,
        "the attestation filesystem identity is wrong",
    )
    _require(
        filesystem["durable_attestation_bytes"] == len(payload),
        "the attestation durable byte count is wrong",
    )
    pre = filesystem["pre_write_available_bytes"]
    measured = filesystem["measured_after_staging_available_bytes"]
    post = filesystem["post_publication_available_bytes"]
    _require(
        isinstance(pre, int) and not isinstance(pre, bool) and pre > 0,
        "attestation pre-write bytes are invalid",
    )
    _require(
        isinstance(measured, int) and not isinstance(measured, bool) and measured >= 0,
        "attestation after-staging bytes are invalid",
    )
    _require(
        post == min(measured, max(pre - len(payload), 0)),
        "attestation post-publication accounting is wrong",
    )
    expected_capacity = derive_capacity(
        basis, pre_write_available_bytes=pre, post_available_bytes=post
    )
    expected_capacity_block = {
        key: value
        for key, value in expected_capacity.items()
        if key not in {"blockers", "storage_preflight_state"}
    }
    _require(capacity == expected_capacity_block, "attestation capacity is wrong")
    _require(
        document["blockers"] == expected_capacity["blockers"],
        "attestation blockers are wrong",
    )
    _require(
        document["storage_preflight_state"]
        == expected_capacity["storage_preflight_state"],
        "attestation state is wrong",
    )
    _require(authorization == AUTHORIZATION, "attestation authorization is wrong")
    _require(
        identity["algorithm"] == SELF_IDENTITY_ALGORITHM
        and identity["scope"] == SELF_IDENTITY_SCOPE
        and identity["canonicalization"] == SELF_IDENTITY_CANONICALIZATION,
        "the attestation self identity contract is wrong",
    )
    unsigned = dict(document)
    unsigned.pop("self_identity")
    _require(
        identity["payload_sha256"] == _sha256(canonical_json(unsigned)),
        "the attestation self identity is wrong",
    )
    return document


def _repository_relative(repository: Path, path: Path, *, label: str) -> Path:
    repository = Path(os.path.abspath(repository))
    raw = path if path.is_absolute() else repository / path
    if ".." in path.parts:
        raise AttestationError(f"the {label} path contains parent traversal")
    normalized = Path(os.path.abspath(raw))
    try:
        relative = normalized.relative_to(repository)
    except ValueError as exc:
        raise AttestationError(f"the {label} path escapes the repository") from exc
    _validate_parts(relative.parts, label=label)
    return relative


def _available_bytes(directory: int) -> int:
    result = os.fstatvfs(directory)
    return int(result.f_bavail) * int(result.f_frsize)


def _device(directory: int) -> str:
    return f"dev:{os.fstat(directory).st_dev}"


def _require_same_device(
    basis_device: str,
    receipt_file_device: str,
    store_device: str,
    output_device: str,
) -> None:
    _require(
        receipt_file_device == basis_device,
        "receipt 258's file is not on its declared device",
    )
    _require(store_device == basis_device, "the store is not on receipt 258's device")
    _require(output_device == store_device, "the attestation is not on the store device")


def _target_absent(directory: int, name: str) -> None:
    try:
        os.stat(name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise AttestationError("the attestation target cannot be inspected safely") from exc
    raise AttestationError("the attestation target already exists")


def _rewrite_and_sync(handle: int, body: bytes) -> None:
    os.ftruncate(handle, 0)
    os.lseek(handle, 0, os.SEEK_SET)
    view = memoryview(body)
    while view:
        written = os.write(handle, view)
        if written <= 0:
            raise AttestationError("the staged attestation write was incomplete")
        view = view[written:]
    os.fsync(handle)


def _rename_no_replace(directory: int, temporary: str, target: str) -> None:
    """Linux atomic same-directory rename which refuses every existing target."""
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        renameat2 = libc.renameat2
    except AttributeError as exc:
        raise OSError(errno.ENOSYS, "renameat2 is unavailable") from exc
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        directory,
        os.fsencode(temporary),
        directory,
        os.fsencode(target),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), target)


def _rollback_to_staging(directory: int, target: str, temporary: str) -> None:
    """Remove the authoritative name first, then make that removal durable."""
    os.rename(
        target,
        temporary,
        src_dir_fd=directory,
        dst_dir_fd=directory,
    )
    os.fsync(directory)


def _cleanup_staging(directory: int, temporary: str) -> None:
    os.unlink(temporary, dir_fd=directory)
    os.fsync(directory)


def _publish_new_attestation(
    *,
    output_directory: int,
    output_name: str,
    store_directory: int,
    basis: SizingBasis,
    code_identity: Mapping[str, str],
    generated_at: str,
) -> tuple[dict[str, Any], bytes]:
    """Publish once through held dirfds; every failure removes this attempt."""
    _target_absent(output_directory, output_name)
    pre_write = _available_bytes(store_directory)
    temporary = f".partial-{output_name}.{os.urandom(8).hex()}.tmp"
    try:
        handle = os.open(
            temporary,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=output_directory,
        )
    except OSError as exc:
        raise AttestationError("the attestation staging file cannot be created safely") from exc
    published = False
    try:
        measured_after = pre_write
        for _ in range(16):
            document, body = render_attestation(
                basis,
                code_identity=code_identity,
                generated_at=generated_at,
                pre_write_available_bytes=pre_write,
                measured_after_staging_available_bytes=measured_after,
            )
            _rewrite_and_sync(handle, body)
            observed = _available_bytes(store_directory)
            confirmed_document, confirmed_body = render_attestation(
                basis,
                code_identity=code_identity,
                generated_at=generated_at,
                pre_write_available_bytes=pre_write,
                measured_after_staging_available_bytes=observed,
            )
            if confirmed_body == body:
                document, body = confirmed_document, confirmed_body
                break
            measured_after = observed
        else:
            raise AttestationError("filesystem availability did not stabilize")
        os.lseek(handle, 0, os.SEEK_SET)
        staged = b""
        while len(staged) < len(body):
            chunk = os.read(handle, min(1024 * 1024, len(body) - len(staged)))
            if not chunk:
                break
            staged += chunk
        _require(staged == body, "the staged attestation failed readback")
        validate_attestation_bytes(
            body, basis=basis, code_identity=code_identity
        )
        try:
            _rename_no_replace(output_directory, temporary, output_name)
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                raise AttestationError("the attestation target already exists") from exc
            raise AttestationError("the attestation no-replace publication failed") from exc
        published = True
        os.fsync(output_directory)
        final_available = _available_bytes(store_directory)
        attested_available = document["filesystem"][
            "post_publication_available_bytes"
        ]
        _require(
            final_available >= attested_available,
            "final post-publication availability undercuts the attestation",
        )
        return document, body
    except Exception:
        if published:
            try:
                _rollback_to_staging(
                    output_directory, output_name, temporary
                )
                published = False
            except OSError as rollback_error:
                raise AttestationError(
                    "post-publication rollback failed"
                ) from rollback_error
        raise
    finally:
        os.close(handle)
        try:
            _cleanup_staging(output_directory, temporary)
        except FileNotFoundError:
            pass
        except OSError as cleanup_error:
            raise AttestationError(
                "the failed attestation staging file was not cleaned"
            ) from cleanup_error


def run_capacity_attestation(
    *, repository: Path, store_root: Path, attestation_path: Path
) -> dict[str, Any]:
    """Revalidate receipt 258, measure its device, and append one attestation."""
    repository = Path(os.path.abspath(repository))
    basis = load_accepted_basis(repository)
    store_relative = _repository_relative(
        repository, store_root, label="store root"
    )
    _require(
        store_relative == Path(basis.destination),
        "the store root is not receipt 258's destination",
    )
    output_relative = _repository_relative(
        repository, attestation_path, label="attestation"
    )
    try:
        beneath = output_relative.relative_to(ATTESTATION_ROOT)
    except ValueError as exc:
        raise AttestationError(
            "the attestation target is outside research/sprint_004"
        ) from exc
    _require(len(beneath.parts) >= 1, "the attestation target has no filename")
    store_directory = _open_directory_chain(
        repository, store_relative.parts, label="store root"
    )
    output_directory = _open_directory_chain(
        repository, output_relative.parent.parts, label="attestation parent"
    )
    try:
        _require_same_device(
            basis.device,
            basis.receipt_file_device,
            _device(store_directory),
            _device(output_directory),
        )
        code_identity = attestation_code_identity(repository)
        generated_at = datetime.now(UTC).isoformat(timespec="microseconds")
        document, body = _publish_new_attestation(
            output_directory=output_directory,
            output_name=output_relative.name,
            store_directory=store_directory,
            basis=basis,
            code_identity=code_identity,
            generated_at=generated_at,
        )
    finally:
        os.close(output_directory)
        os.close(store_directory)
    return {
        "attestation": document,
        "attestation_file": {
            "path": str(output_relative),
            "sha256": _sha256(body),
            "bytes": len(body),
        },
    }
