from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from cryptofactors.acquisition import binance_usdm_capacity_attestation as attestation
from cryptofactors.acquisition import binance_usdm_harmonic_sizing as sizing


REPOSITORY = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def basis() -> attestation.SizingBasis:
    return attestation.load_accepted_basis(REPOSITORY)


def _code_identity() -> dict[str, str]:
    return {
        "policy_identity": attestation.ATTESTATION_POLICY,
        "attestation_source_sha256": "a" * 64,
        "attestation_cli_sha256": "b" * 64,
        "attestation_source_path": str(attestation.SOURCE_RELATIVE_PATH),
        "attestation_cli_path": str(attestation.CLI_RELATIVE_PATH),
    }


def _resign(document: dict[str, Any]) -> bytes:
    """Give a forged document internally consistent length and self-hash fields."""
    for _ in range(16):
        filesystem = document["filesystem"]
        durable = int(filesystem["durable_attestation_bytes"])
        filesystem["post_publication_available_bytes"] = min(
            int(filesystem["measured_after_staging_available_bytes"]),
            max(int(filesystem["pre_write_available_bytes"]) - durable, 0),
        )
        unsigned = dict(document)
        unsigned.pop("self_identity")
        document["self_identity"]["payload_sha256"] = hashlib.sha256(
            attestation.canonical_json(unsigned)
        ).hexdigest()
        body = attestation.canonical_json(document)
        if len(body) == durable:
            return body
        filesystem["durable_attestation_bytes"] = len(body)
    raise AssertionError("forged attestation length did not converge")


def _load_cli() -> Any:
    path = REPOSITORY / attestation.CLI_RELATIVE_PATH
    spec = importlib.util.spec_from_file_location("capacity_attestation_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_receipt_258_exact_bytes_and_stable_basis_are_bound(
    basis: attestation.SizingBasis,
) -> None:
    receipt = REPOSITORY / attestation.RECEIPT_RELATIVE_PATH
    raw = receipt.read_bytes()
    assert len(raw) == attestation.EXPECTED_RECEIPT_BYTES == basis.receipt_bytes
    assert hashlib.sha256(raw).hexdigest() == basis.receipt_sha256
    assert basis.receipt_schema == attestation.EXPECTED_RECEIPT_SCHEMA
    assert basis.receipt_policy == attestation.EXPECTED_RECEIPT_POLICY
    assert basis.destination == attestation.EXPECTED_DESTINATION
    assert basis.device == attestation.EXPECTED_DEVICE
    assert basis.receipt_file_device == f"dev:{receipt.stat().st_dev}" == basis.device
    assert basis.stable_components == attestation.STABLE_COMPONENTS
    assert sum(basis.stable_components.values()) == basis.stable_requirement_bytes
    assert basis.stable_requirement_bytes == 139_577_980_018
    receipt_document = json.loads(raw.decode("utf-8"))
    projection = sizing.stable_receipt_projection(receipt_document)
    local_projection = attestation.stable_receipt_projection(receipt_document)
    assert local_projection == projection
    assert attestation.canonical_json(local_projection) == sizing.canonical_json(
        projection
    )
    assert set(projection) == set(sizing.STABLE_RECEIPT_FIELDS) | {"capacity"}
    assert set(projection["capacity"]) == set(sizing.STABLE_CAPACITY_FIELDS)
    assert basis.stable_receipt_identity == sizing.stable_receipt_identity(
        receipt_document
    )
    assert basis.stable_receipt_identity == attestation.stable_receipt_identity(
        receipt_document
    )
    changed_authority = dict(receipt_document)
    changed_authority["authority"] = dict(receipt_document["authority"])
    changed_authority["authority"]["plan_entries"] += 1
    assert sizing.stable_receipt_identity(changed_authority) != (
        basis.stable_receipt_identity
    )
    assert attestation.stable_receipt_identity(changed_authority) != (
        basis.stable_receipt_identity
    )
    corrupted = bytearray(raw)
    corrupted[-2] = ord(" ")
    with pytest.raises(attestation.AttestationError, match="hash changed"):
        attestation.validate_receipt_bytes(
            bytes(corrupted), receipt_file_device=basis.receipt_file_device
        )


def test_receipt_component_state_and_authorization_reconciliation_are_fail_closed(
    basis: attestation.SizingBasis,
) -> None:
    receipt = json.loads(
        (REPOSITORY / attestation.RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    for mutation, message in (
        (("capacity", "new_binance_raw_bytes", 1), "stable component"),
        (("capacity", "operating_reserve_bytes", 1), "reserve"),
        (("capacity", "total_future_storage_bytes", 1), "total"),
        ((None, "storage_preflight_state", "sufficient"), "internally blocked"),
        ((None, "blockers", []), "blockers"),
        ((None, "authorization", "acquisition allowed"), "authorization"),
    ):
        changed = copy.deepcopy(receipt)
        section, key, value = mutation
        target = changed if section is None else changed[section]
        target[key] = value
        with pytest.raises(attestation.AttestationError, match=message):
            attestation._validate_receipt_semantics(
                changed, receipt_file_device=basis.receipt_file_device
            )
    assert basis.receipt_code_identity["sizing_source_sha256"] == (
        attestation.EXPECTED_SIZING_SOURCE_SHA256
    )
    assert basis.receipt_code_identity["sizing_cli_sha256"] == (
        attestation.EXPECTED_SIZING_CLI_SHA256
    )


def test_dynamic_reserve_boundary_has_no_operator_override(
    basis: attestation.SizingBasis,
) -> None:
    minimum_boundary = 5 * attestation.MINIMUM_OPERATING_RESERVE_BYTES
    assert attestation.operating_reserve_bytes(minimum_boundary - 1) == (
        attestation.MINIMUM_OPERATING_RESERVE_BYTES
    )
    assert attestation.operating_reserve_bytes(minimum_boundary + 1) == (
        attestation.MINIMUM_OPERATING_RESERVE_BYTES + 1
    )
    reserve = attestation.operating_reserve_bytes(200_000_000_001)
    total = basis.stable_requirement_bytes + reserve
    sufficient = attestation.derive_capacity(
        basis,
        pre_write_available_bytes=200_000_000_001,
        post_available_bytes=total,
    )
    blocked = attestation.derive_capacity(
        basis,
        pre_write_available_bytes=200_000_000_001,
        post_available_bytes=total - 1,
    )
    assert sufficient["storage_preflight_state"] == "sufficient"
    assert sufficient["blockers"] == []
    assert blocked["storage_preflight_state"] == "blocked"
    assert blocked["blockers"] == [attestation.BLOCKER_CAPACITY]


def test_canonical_attestation_self_length_and_post_write_accounting(
    basis: attestation.SizingBasis,
) -> None:
    document, body = attestation.render_attestation(
        basis,
        code_identity=_code_identity(),
        generated_at="2026-08-24T12:00:00.000000+00:00",
        pre_write_available_bytes=200_000_000_000,
        measured_after_staging_available_bytes=199_999_990_000,
    )
    assert body == attestation.canonical_json(document)
    assert document["filesystem"]["durable_attestation_bytes"] == len(body)
    assert document["filesystem"]["post_publication_available_bytes"] == min(
        199_999_990_000, 200_000_000_000 - len(body)
    )
    assert (
        attestation.validate_attestation_bytes(
            body, basis=basis, code_identity=_code_identity()
        )
        == document
    )
    unsigned = dict(document)
    unsigned.pop("self_identity")
    assert document["self_identity"]["payload_sha256"] == hashlib.sha256(
        attestation.canonical_json(unsigned)
    ).hexdigest()


def test_basis_code_arithmetic_and_authorization_fields_are_deterministic(
    basis: attestation.SizingBasis,
) -> None:
    arguments = {
        "code_identity": _code_identity(),
        "generated_at": "2026-08-24T12:00:00.000000+00:00",
        "pre_write_available_bytes": 100_000_000_000,
        "measured_after_staging_available_bytes": 99_999_990_000,
    }
    first, first_body = attestation.render_attestation(basis, **arguments)
    second, second_body = attestation.render_attestation(basis, **arguments)
    assert first_body == second_body
    assert first["basis"]["stable_receipt_identity"] == (
        basis.stable_receipt_identity
    )
    assert first["basis"]["receipt_file_device"] == basis.receipt_file_device
    assert first["basis"]["stable_capacity_components"] == (
        attestation.STABLE_COMPONENTS
    )
    assert first["code_identity"] == _code_identity()
    assert first["authorization"] == {
        "gate_2_accepted": False,
        "acquisition_authorized": False,
        "statement": (
            "this attestation is measurement evidence only; it accepts no gate, "
            "authorizes no acquisition, and changes no ticket state"
        ),
    }


def test_every_closed_attestation_section_rejects_resigned_mutation(
    basis: attestation.SizingBasis,
) -> None:
    valid, _body = attestation.render_attestation(
        basis,
        code_identity=_code_identity(),
        generated_at="2026-08-24T12:00:00.000000+00:00",
        pre_write_available_bytes=200_000_000_000,
        measured_after_staging_available_bytes=199_999_990_000,
    )

    def changed(mutator: Any) -> bytes:
        forged = copy.deepcopy(valid)
        mutator(forged)
        return _resign(forged)

    mutations = (
        lambda row: row.__setitem__("extra", 1),
        lambda row: row.pop("authorization"),
        lambda row: row.__setitem__("schema_version", "other"),
        lambda row: row.__setitem__("ticket", "OTHER"),
        lambda row: row.__setitem__("generated_at", "2026-08-24T12:00:00+01:00"),
        lambda row: row["basis"].__setitem__("receipt_sha256", "0" * 64),
        lambda row: row["basis"].__setitem__("extra", 1),
        lambda row: row["basis"].pop("receipt_bytes"),
        lambda row: row["code_identity"].__setitem__(
            "attestation_source_sha256", "0" * 64
        ),
        lambda row: row["code_identity"].__setitem__("extra", 1),
        lambda row: row["code_identity"].pop("attestation_cli_sha256"),
        lambda row: row["filesystem"].__setitem__("destination", "elsewhere"),
        lambda row: row["filesystem"].__setitem__("extra", 1),
        lambda row: row["filesystem"].pop("accounting"),
        lambda row: row["capacity"].__setitem__("stable_requirement_bytes", 1),
        lambda row: row["capacity"].__setitem__("extra", 1),
        lambda row: row["capacity"].pop("equation"),
        lambda row: row.__setitem__("blockers", [attestation.BLOCKER_CAPACITY]),
        lambda row: row.__setitem__("storage_preflight_state", "blocked"),
        lambda row: row["authorization"].__setitem__(
            "statement", "acquisition authorized"
        ),
        lambda row: row["authorization"].__setitem__("extra", 1),
        lambda row: row["authorization"].pop("statement"),
        lambda row: row["self_identity"].__setitem__("algorithm", "other"),
        lambda row: row["self_identity"].__setitem__("extra", 1),
        lambda row: row["self_identity"].pop("scope"),
    )
    for mutate in mutations:
        with pytest.raises(attestation.AttestationError):
            attestation.validate_attestation_bytes(
                changed(mutate), basis=basis, code_identity=_code_identity()
            )


def test_store_output_and_receipt_devices_must_all_match(
    basis: attestation.SizingBasis,
) -> None:
    attestation._require_same_device(
        basis.device, basis.receipt_file_device, basis.device, basis.device
    )
    with pytest.raises(attestation.AttestationError, match="receipt 258's file"):
        attestation._require_same_device(
            basis.device, "dev:0", basis.device, basis.device
        )
    with pytest.raises(attestation.AttestationError, match="store"):
        attestation._require_same_device(
            basis.device, basis.receipt_file_device, "dev:1", basis.device
        )
    with pytest.raises(attestation.AttestationError, match="attestation"):
        attestation._require_same_device(
            basis.device, basis.receipt_file_device, basis.device, "dev:2"
        )


def test_transactional_publication_refuses_existing_file_and_symlink(
    basis: attestation.SizingBasis, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "store"
    output = tmp_path / "output"
    store.mkdir()
    output.mkdir()
    store_fd = os.open(store, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    output_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    monkeypatch.setattr(attestation, "_available_bytes", lambda _fd: 200_000_000_000)
    try:
        document, body = attestation._publish_new_attestation(
            output_directory=output_fd,
            output_name="capacity.json",
            store_directory=store_fd,
            basis=basis,
            code_identity=_code_identity(),
            generated_at="2026-08-24T12:00:00.000000+00:00",
        )
        assert (output / "capacity.json").read_bytes() == body
        assert (
            attestation.validate_attestation_bytes(
                body, basis=basis, code_identity=_code_identity()
            )
            == document
        )
        with pytest.raises(attestation.AttestationError, match="already exists"):
            attestation._publish_new_attestation(
                output_directory=output_fd,
                output_name="capacity.json",
                store_directory=store_fd,
                basis=basis,
                code_identity=_code_identity(),
                generated_at="2026-08-24T12:00:01.000000+00:00",
            )
        (output / "linked.json").symlink_to(output / "capacity.json")
        with pytest.raises(attestation.AttestationError, match="already exists"):
            attestation._publish_new_attestation(
                output_directory=output_fd,
                output_name="linked.json",
                store_directory=store_fd,
                basis=basis,
                code_identity=_code_identity(),
                generated_at="2026-08-24T12:00:02.000000+00:00",
            )
        assert (output / "capacity.json").read_bytes() == body
        assert (output / "linked.json").is_symlink()
    finally:
        os.close(output_fd)
        os.close(store_fd)


def test_failed_transaction_cleans_staging_and_preserves_prior_evidence(
    basis: attestation.SizingBasis, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "store"
    output = tmp_path / "output"
    store.mkdir()
    output.mkdir()
    receipt = REPOSITORY / attestation.RECEIPT_RELATIVE_PATH
    receipt_before = hashlib.sha256(receipt.read_bytes()).hexdigest()
    store_fd = os.open(store, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    output_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    monkeypatch.setattr(attestation, "_available_bytes", lambda _fd: 200_000_000_000)

    def fail_rename(_directory: int, _temporary: str, _target: str) -> None:
        raise OSError("injected publication failure")

    monkeypatch.setattr(attestation, "_rename_no_replace", fail_rename)
    try:
        with pytest.raises(attestation.AttestationError, match="publication failed"):
            attestation._publish_new_attestation(
                output_directory=output_fd,
                output_name="capacity.json",
                store_directory=store_fd,
                basis=basis,
                code_identity=_code_identity(),
                generated_at="2026-08-24T12:00:00.000000+00:00",
            )
    finally:
        os.close(output_fd)
        os.close(store_fd)
    assert list(output.iterdir()) == []
    assert hashlib.sha256(receipt.read_bytes()).hexdigest() == receipt_before


def test_final_post_publication_capacity_loss_removes_the_target(
    basis: attestation.SizingBasis, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "store"
    output = tmp_path / "output"
    store.mkdir()
    output.mkdir()
    store_fd = os.open(store, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    output_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    observations = iter(
        (200_000_000_000, 200_000_000_000, 199_000_000_000)
    )
    monkeypatch.setattr(attestation, "_available_bytes", lambda _fd: next(observations))
    try:
        with pytest.raises(attestation.AttestationError, match="undercuts"):
            attestation._publish_new_attestation(
                output_directory=output_fd,
                output_name="capacity.json",
                store_directory=store_fd,
                basis=basis,
                code_identity=_code_identity(),
                generated_at="2026-08-24T12:00:00.000000+00:00",
            )
    finally:
        os.close(output_fd)
        os.close(store_fd)
    assert list(output.iterdir()) == []


def test_post_publication_rollback_failure_is_explicit(
    basis: attestation.SizingBasis, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "store"
    output = tmp_path / "output"
    store.mkdir()
    output.mkdir()
    store_fd = os.open(store, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    output_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    observations = iter(
        (200_000_000_000, 200_000_000_000, 199_000_000_000)
    )
    monkeypatch.setattr(attestation, "_available_bytes", lambda _fd: next(observations))

    def fail_rollback(_directory: int, _target: str, _temporary: str) -> None:
        raise OSError("injected rollback failure")

    monkeypatch.setattr(attestation, "_rollback_to_staging", fail_rollback)
    try:
        with pytest.raises(attestation.AttestationError, match="rollback failed"):
            attestation._publish_new_attestation(
                output_directory=output_fd,
                output_name="capacity.json",
                store_directory=store_fd,
                basis=basis,
                code_identity=_code_identity(),
                generated_at="2026-08-24T12:00:00.000000+00:00",
            )
    finally:
        os.close(output_fd)
        os.close(store_fd)
    assert (output / "capacity.json").is_file()


def test_staging_cleanup_failure_occurs_after_authoritative_name_is_removed(
    basis: attestation.SizingBasis, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "store"
    output = tmp_path / "output"
    store.mkdir()
    output.mkdir()
    store_fd = os.open(store, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    output_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    observations = iter(
        (200_000_000_000, 200_000_000_000, 199_000_000_000)
    )
    monkeypatch.setattr(attestation, "_available_bytes", lambda _fd: next(observations))

    def fail_cleanup(_directory: int, _temporary: str) -> None:
        raise OSError("injected staging cleanup failure")

    monkeypatch.setattr(attestation, "_cleanup_staging", fail_cleanup)
    try:
        with pytest.raises(attestation.AttestationError, match="staging file"):
            attestation._publish_new_attestation(
                output_directory=output_fd,
                output_name="capacity.json",
                store_directory=store_fd,
                basis=basis,
                code_identity=_code_identity(),
                generated_at="2026-08-24T12:00:00.000000+00:00",
            )
    finally:
        os.close(output_fd)
        os.close(store_fd)
    assert not (output / "capacity.json").exists()
    assert any(path.name.startswith(".partial-capacity.json") for path in output.iterdir())


def test_run_capacity_attestation_end_to_end_in_synthetic_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    receipt_target = repository / attestation.RECEIPT_RELATIVE_PATH
    source_target = repository / attestation.SOURCE_RELATIVE_PATH
    cli_target = repository / attestation.CLI_RELATIVE_PATH
    store = repository / attestation.EXPECTED_DESTINATION
    for directory in {
        receipt_target.parent,
        source_target.parent,
        cli_target.parent,
        store,
    }:
        directory.mkdir(parents=True, exist_ok=True)
    original_receipt = REPOSITORY / attestation.RECEIPT_RELATIVE_PATH
    original_hash = hashlib.sha256(original_receipt.read_bytes()).hexdigest()
    shutil.copyfile(original_receipt, receipt_target)
    shutil.copyfile(REPOSITORY / attestation.SOURCE_RELATIVE_PATH, source_target)
    shutil.copyfile(REPOSITORY / attestation.CLI_RELATIVE_PATH, cli_target)
    monkeypatch.setattr(attestation, "_available_bytes", lambda _fd: 200_000_000_000)
    result = attestation.run_capacity_attestation(
        repository=repository,
        store_root=Path(attestation.EXPECTED_DESTINATION),
        attestation_path=Path("research/sprint_004/synthetic_capacity.json"),
    )
    output = repository / result["attestation_file"]["path"]
    assert output.is_file() and not output.is_symlink()
    synthetic_basis = attestation.load_accepted_basis(repository)
    synthetic_code = attestation.attestation_code_identity(repository)
    assert attestation.validate_attestation_bytes(
        output.read_bytes(), basis=synthetic_basis, code_identity=synthetic_code
    ) == result["attestation"]
    assert result["attestation"]["storage_preflight_state"] == "sufficient"
    assert result["attestation"]["authorization"] == attestation.AUTHORIZATION
    assert hashlib.sha256(receipt_target.read_bytes()).hexdigest() == original_hash
    assert hashlib.sha256(original_receipt.read_bytes()).hexdigest() == original_hash


def test_paths_are_beneath_fixed_roots_and_code_has_no_network_surface(
    basis: attestation.SizingBasis,
) -> None:
    assert attestation._repository_relative(
        REPOSITORY, Path(basis.destination), label="store root"
    ) == Path(basis.destination)
    with pytest.raises(attestation.AttestationError, match="escapes"):
        attestation._repository_relative(
            REPOSITORY, Path("/tmp/outside.json"), label="attestation"
        )
    with pytest.raises(attestation.AttestationError, match="parent traversal"):
        attestation._repository_relative(
            REPOSITORY,
            Path("research/sprint_004/../outside.json"),
            label="attestation",
        )
    parser = _load_cli().build_parser()
    options = {
        option
        for action in parser._actions
        for option in action.option_strings
        if option not in {"-h", "--help"}
    }
    assert options == {"--store-root", "--attestation-path"}
    source = (REPOSITORY / attestation.SOURCE_RELATIVE_PATH).read_text(encoding="utf-8")
    assert "requests" not in source
    assert "urllib" not in source
    assert "socket" not in source


def test_cli_redacts_error_context_and_reports_complete_states(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = _load_cli()

    def fail(**_kwargs: Any) -> dict[str, Any]:
        raise attestation.AttestationError(
            "authority is invalid", context={"api_key": "never-print-this"}
        )

    monkeypatch.setattr(cli, "run_capacity_attestation", fail)
    assert cli.main(["--attestation-path", "research/sprint_004/new.json"]) == 1
    error = capsys.readouterr()
    assert "ERROR: authority is invalid" in error.err
    assert "never-print-this" not in error.err

    monkeypatch.setattr(
        cli,
        "run_capacity_attestation",
        lambda **_kwargs: {
            "attestation": {
                "storage_preflight_state": "blocked",
                "capacity": {"total_future_storage_bytes": 10},
                "filesystem": {"post_publication_available_bytes": 9},
                "blockers": [attestation.BLOCKER_CAPACITY],
            },
            "attestation_file": {
                "path": "research/sprint_004/new.json",
                "sha256": "c" * 64,
                "bytes": 123,
            },
        },
    )
    assert cli.main(["--attestation-path", "research/sprint_004/new.json"]) == 0
    success = capsys.readouterr()
    assert "storage_preflight_state=blocked" in success.err
    assert "authorizes no acquisition and accepts no gate" in success.err
