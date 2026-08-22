"""CEX-002 ADR-0022 — prove the reviewed path-bound source-authority transition.

The pinned production identities cannot be reproduced at fixture scale, so each fixture
builds a structurally identical store and re-points the frozen constants at its own
artifacts. One test asserts the literal review-208 values on their own.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from cryptofactors.acquisition import (
    binance_usdm_harmonic_path_bound_transition as transition,
)
from cryptofactors.acquisition.binance_usdm_harmonic_path_bound_transition import (
    CHECKPOINT_EVIDENCE_ROOT,
    LEDGER_EVIDENCE_ROOT,
    LOCK_EVIDENCE_ROOT,
    PRIOR_RECEIPT_COUNT,
    REPORT_EVIDENCE_ROOT,
    STATE_COMPLETE,
    STATE_FRESH,
    STATE_LEDGER_ADVANCED,
    TARGET_RECEIPT_COUNT,
    TRANSITION_ID,
    TransitionError,
    TransitionPaths,
    apply_path_bound_transition,
    canonical_json,
    preflight,
    preserve_prior_artifact,
    target_source_identity,
)

_PRIOR_IDENTITY = {
    "module_sha256": "0" * 64,
    "code_config_digest": "d" * 64,
    "reviewed_authority_table_version": "review137-v1",
    "delivery_table_sha256": "e" * 64,
    "alias_table_sha256": "f" * 64,
}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write(path: Path, document: Any) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json(document)
    path.write_bytes(payload)
    return payload


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A structurally exact pinned pre-state with every frozen constant re-pointed."""
    root = tmp_path / "store"
    root.mkdir()
    source_path = tmp_path / "qualification.py"
    source_path.write_text("# reviewed path-bound qualification source\n")
    report_path = tmp_path / "62_report.json"
    manifest_path = tmp_path / "manifest_detail.jsonl.gz"
    report_bytes = _write(report_path, {"ticket": "CEX-002", "gate_status": "BLOCKED"})
    # A real deterministic gzip, so the pinned uncompressed identity is genuinely proved.
    expanded = b"".join(
        json.dumps({"record_type": "row", "record": {"n": index}}, sort_keys=True).encode()
        + b"\n"
        for index in range(64)
    )
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=9, mtime=0) as handle:
        handle.write(expanded)
    manifest_path.write_bytes(buffer.getvalue())

    binding = {
        "migration_id": "cex002_reviewed_v4_migration",
        "allowance_id": "cex002_architecture_amendment_v3",
        "source_receipts": [
            {
                "prepared_at": "2026-08-21T00:00:00+00:00",
                "source_identity": {**_PRIOR_IDENTITY, "module_sha256": "1" * 64},
            },
            {
                "prepared_at": "2026-08-21T12:00:00+00:00",
                "source_identity": dict(_PRIOR_IDENTITY),
            },
        ],
    }
    charges = {
        f"data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-{index:02d}.zip": {
            "planned_bytes": 100 + index,
            "transferred_bytes": 100 + index,
            "disposition": "transferred",
            "sha256": f"{index:064d}",
        }
        for index in range(1, 4)
    }
    ledger_document = {
        "ticket": "CEX-002",
        "kind": "budget_ledger",
        "budget_bytes": 268_435_456,
        "charges": charges,
        "reservations": {},
        "legacy_max_bytes": 0,
        "legacy_state": "resolved",
        "binding": binding,
        "integrity": {"state_sha256": "9" * 64},
    }
    lock_document = {
        "ticket": "CEX-002",
        "kind": "sample_plan_lock",
        "plan_version": 4,
        "plan_digest": "2" * 64,
        "locked_at": "2026-08-21T12:00:00+00:00",
        "inputs": {
            "inventory_digest": "a" * 64,
            "listing_digest": "b" * 64,
            "membership_digest": "c" * 64,
            "code_config_digest": _PRIOR_IDENTITY["code_config_digest"],
            "budget_digest": "5" * 64,
            "retained_digest": "6" * 64,
        },
        "plan": {"entries": [{"key": key, "action": "download"} for key in charges]},
        "retained_snapshot": {"key": ["evidence"]},
        "budget_snapshot": {
            "ledger_id": "cex002_architecture_amendment_v3",
            "amendment_binding": binding,
        },
        "history": [{"plan_version": index} for index in range(3)],
    }
    files = {
        "lock": root / "cex002_sample_plan_lock.json",
        "ledger": root / "cex002_amendment_ledger.json",
        "legacy": root / "cex002_budget_ledger.json",
        "checkpoint": root / "cex002_qualification_progress.json",
        "journal": root / "cex002_retry_journal.json",
        "plan": root / "cex002_sample_plan.json",
        "listing": root / "cex002_listing_checkpoint.json",
        "metadata": root / "cex002_official_contract_metadata.json",
    }
    lock_bytes = _write(files["lock"], lock_document)
    ledger_bytes = _write(files["ledger"], ledger_document)
    legacy_bytes = _write(files["legacy"], {"kind": "budget_ledger", "charges": {}})
    checkpoint_bytes = _write(files["checkpoint"], {"kind": "sample_checkpoint", "objects": {}})
    journal_bytes = _write(files["journal"], {"incidents": []})
    plan_bytes = _write(files["plan"], {"entries": []})
    listing_bytes = _write(files["listing"], {"entries": {}})
    metadata_bytes = _write(files["metadata"], {"symbol_snapshot": {}})

    pins = {
        "PRIOR_REPORT_SHA256": _sha256(report_bytes),
        "PRIOR_REPORT_BYTES": len(report_bytes),
        "PRIOR_MANIFEST_SHA256": _sha256(manifest_path.read_bytes()),
        "PRIOR_MANIFEST_BYTES": manifest_path.stat().st_size,
        "PRIOR_MANIFEST_UNCOMPRESSED_SHA256": _sha256(expanded),
        "PRIOR_MANIFEST_UNCOMPRESSED_BYTES": len(expanded),
        "PRIOR_LOCK_SHA256": _sha256(lock_bytes),
        "PRIOR_LOCK_BYTES": len(lock_bytes),
        "PRIOR_AMENDMENT_LEDGER_SHA256": _sha256(ledger_bytes),
        "PRIOR_AMENDMENT_LEDGER_BYTES": len(ledger_bytes),
        "PRIOR_LEGACY_LEDGER_SHA256": _sha256(legacy_bytes),
        "PRIOR_LEGACY_LEDGER_BYTES": len(legacy_bytes),
        "PRIOR_CHECKPOINT_SHA256": _sha256(checkpoint_bytes),
        "PRIOR_CHECKPOINT_BYTES": len(checkpoint_bytes),
        "PRIOR_RETRY_JOURNAL_SHA256": _sha256(journal_bytes),
        "PRIOR_RETRY_JOURNAL_BYTES": len(journal_bytes),
        "PRIOR_SAMPLE_PLAN_SHA256": _sha256(plan_bytes),
        "PRIOR_SAMPLE_PLAN_BYTES": len(plan_bytes),
        "PRIOR_LISTING_CHECKPOINT_SHA256": _sha256(listing_bytes),
        "PRIOR_LISTING_CHECKPOINT_BYTES": len(listing_bytes),
        "PRIOR_METADATA_SHA256": _sha256(metadata_bytes),
        "PRIOR_METADATA_BYTES": len(metadata_bytes),
        "PRIOR_PLAN_DIGEST": lock_document["plan_digest"],
        "PRIOR_PLAN_ENTRIES": len(charges),
        "PRIOR_HISTORY_ROWS": 3,
        "PRIOR_CODE_CONFIG_DIGEST": _PRIOR_IDENTITY["code_config_digest"],
        "PRIOR_LEDGER_CHARGES": len(charges),
        "PRIOR_LEDGER_CHARGED_BYTES": sum(
            int(row["transferred_bytes"]) for row in charges.values()
        ),
        "TARGET_MODULE_SHA256": _sha256(source_path.read_bytes()),
        "TARGET_CODE_CONFIG_DIGEST": "7" * 64,
    }
    for name, value in pins.items():
        monkeypatch.setattr(transition, name, value)

    paths = TransitionPaths(
        store_root=root,
        report_path=report_path,
        manifest_detail_path=manifest_path,
        qualification_source_path=source_path,
    )
    return {
        "paths": paths,
        "root": root,
        "files": files,
        "pins": pins,
        "expanded": expanded,
    }


def _surface(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): _sha256(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_pinned_review208_identities_are_literal() -> None:
    assert transition.TRANSITION_ID == "cex002_adr0022_path_bound_source_transition"
    assert transition.PRIOR_REPORT_BYTES == 13_559_766
    assert transition.PRIOR_LOCK_BYTES == 426_276
    assert transition.PRIOR_AMENDMENT_LEDGER_BYTES == 26_103
    assert transition.PRIOR_LEGACY_LEDGER_BYTES == 777
    assert transition.PRIOR_CHECKPOINT_BYTES == 487_815
    assert transition.PRIOR_RETRY_JOURNAL_BYTES == 13_737
    assert transition.PRIOR_SAMPLE_PLAN_BYTES == 51_124
    assert transition.PRIOR_LISTING_CHECKPOINT_BYTES == 33_206_753
    assert transition.PRIOR_METADATA_BYTES == 99_357
    assert (
        transition.PRIOR_MANIFEST_UNCOMPRESSED_BYTES == 466_713_055
    )
    assert transition.PRIOR_PLAN_VERSION == 4
    assert transition.PRIOR_PLAN_ENTRIES == 106
    assert transition.PRIOR_HISTORY_ROWS == 3
    assert transition.PRIOR_RECEIPT_COUNT == 2
    assert transition.TARGET_RECEIPT_COUNT == 3
    assert transition.PRIOR_LEDGER_CHARGES == 84
    assert transition.PRIOR_LEDGER_RESERVATIONS == 0
    assert transition.PRIOR_LEDGER_CHARGED_BYTES == 1_049_324
    assert transition.PRIOR_CODE_CONFIG_DIGEST == (
        "da33197203e0c9651dc84f42e6e2ce26867339cebe4c68286a00639046c08258"
    )
    # The target identity is the reviewed path-bound qualification source.
    assert transition.TARGET_MODULE_SHA256 == (
        "2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74"
    )
    assert transition.TARGET_CODE_CONFIG_DIGEST == (
        "86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb"
    )
    identity = transition.target_source_identity()
    assert identity["reviewed_authority_table_version"] == "review137-v1"
    assert identity["delivery_table_sha256"] == (
        "678d07e0679b0e116a372a333c3c33f74f5e421dadba393cb9516e56ae8b9a01"
    )
    assert identity["alias_table_sha256"] == (
        "e9837ee2ac0711e41981e27979532be5095d61f04fb82442919c9f301f5998f8"
    )


def test_pinned_pre_state_preflights_as_fresh(store: dict[str, Any]) -> None:
    authority = preflight(store["paths"])
    assert authority.state == STATE_FRESH
    assert len(authority.prior_receipts) == PRIOR_RECEIPT_COUNT


@pytest.mark.parametrize(
    "target",
    ["lock", "ledger", "legacy", "checkpoint", "journal", "plan", "listing", "metadata"],
)
def test_every_pinned_identity_mismatch_stops_before_any_mutation(
    store: dict[str, Any], target: str
) -> None:
    path = store["files"][target]
    path.write_bytes(path.read_bytes() + b" ")
    before = _surface(store["root"])
    with pytest.raises(TransitionError):
        apply_path_bound_transition(store["paths"])
    # Nothing preserved, nothing advanced.
    assert _surface(store["root"]) == before
    assert not (store["root"] / LOCK_EVIDENCE_ROOT).exists()
    assert not (store["root"] / LEDGER_EVIDENCE_ROOT).exists()


@pytest.mark.parametrize("target", ["report", "manifest", "source"])
def test_external_pinned_identity_mismatch_also_stops(
    store: dict[str, Any], target: str
) -> None:
    paths = store["paths"]
    path = {
        "report": paths.report_path,
        "manifest": paths.manifest_detail_path,
        "source": paths.qualification_source_path,
    }[target]
    path.write_bytes(path.read_bytes() + b" ")
    before = _surface(store["root"])
    with pytest.raises(TransitionError, match="pinned transition identity|is missing"):
        apply_path_bound_transition(paths)
    assert _surface(store["root"]) == before


def test_transition_advances_only_the_executing_identity(store: dict[str, Any]) -> None:
    paths = store["paths"]
    lock_before = json.loads(paths.lock_path.read_text())
    ledger_before = json.loads(paths.amendment_ledger_path.read_text())
    immutable_before = {
        str(path): _sha256(path.read_bytes())
        for path, _digest, _size, _label in transition.immutable_pinned_files(paths)
    }

    receipt = apply_path_bound_transition(
        paths, now=datetime(2026, 8, 22, tzinfo=UTC)
    )

    assert receipt["executed"] is True
    assert receipt["state"] == STATE_COMPLETE
    lock_after = json.loads(paths.lock_path.read_text())
    ledger_after = json.loads(paths.amendment_ledger_path.read_text())

    # Exactly the first two receipts preserved, exactly one appended for the target.
    receipts = ledger_after["binding"]["source_receipts"]
    assert len(receipts) == TARGET_RECEIPT_COUNT
    assert receipts[:PRIOR_RECEIPT_COUNT] == ledger_before["binding"]["source_receipts"]
    assert receipts[-1]["source_identity"] == target_source_identity()
    # Ledger accounting is untouched.
    for field_name in ("charges", "reservations", "budget_bytes", "legacy_max_bytes"):
        assert ledger_after[field_name] == ledger_before[field_name]

    # The lock changed only its code/config digest, binding, and transition metadata.
    assert lock_after["inputs"]["code_config_digest"] == (
        transition.TARGET_CODE_CONFIG_DIGEST
    )
    for field_name in ("plan", "plan_digest", "history", "retained_snapshot", "locked_at"):
        assert lock_after[field_name] == lock_before[field_name]
    for field_name, value in lock_before["inputs"].items():
        if field_name != "code_config_digest":
            assert lock_after["inputs"][field_name] == value
    snapshot_before = dict(lock_before["budget_snapshot"])
    snapshot_after = dict(lock_after["budget_snapshot"])
    assert snapshot_after["amendment_binding"] == ledger_after["binding"]
    assert snapshot_after["path_bound_transition"]["transition_id"] == TRANSITION_ID
    assert snapshot_after["path_bound_transition"]["download_authorized"] is False
    for field_name, value in snapshot_before.items():
        if field_name != "amendment_binding":
            assert snapshot_after[field_name] == value

    # Every other pinned artifact is byte-identical.
    for path, digest in immutable_before.items():
        assert _sha256(Path(path).read_bytes()) == digest


def test_prior_artifacts_are_preserved_at_their_content_addresses(
    store: dict[str, Any]
) -> None:
    paths = store["paths"]
    originals = {
        REPORT_EVIDENCE_ROOT: paths.report_path.read_bytes(),
        CHECKPOINT_EVIDENCE_ROOT: paths.checkpoint_path.read_bytes(),
        LOCK_EVIDENCE_ROOT: paths.lock_path.read_bytes(),
        LEDGER_EVIDENCE_ROOT: paths.amendment_ledger_path.read_bytes(),
    }
    receipt = apply_path_bound_transition(paths)
    for root, payload in originals.items():
        preserved = paths.evidence(root, _sha256(payload))
        assert preserved.is_file()
        assert preserved.read_bytes() == payload
    assert set(receipt["preserved_evidence"]) == {"report", "checkpoint", "lock", "ledger"}
    assert not list((store["root"] / LOCK_EVIDENCE_ROOT).glob(".partial-*"))


def test_evidence_collision_with_different_bytes_fails_closed(
    store: dict[str, Any]
) -> None:
    paths = store["paths"]
    digest = _sha256(paths.lock_path.read_bytes())
    dest = paths.evidence(LOCK_EVIDENCE_ROOT, digest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"a different prior lock\n")
    with pytest.raises(TransitionError, match="already occupies its content address"):
        preserve_prior_artifact(
            paths,
            source=paths.lock_path,
            root=LOCK_EVIDENCE_ROOT,
            digest=digest,
            label="prior lock",
        )
    # The occupying bytes are never overwritten.
    assert dest.read_bytes() == b"a different prior lock\n"


def test_identical_existing_evidence_is_reused_after_rehash(store: dict[str, Any]) -> None:
    paths = store["paths"]
    payload = paths.lock_path.read_bytes()
    digest = _sha256(payload)
    dest = paths.evidence(LOCK_EVIDENCE_ROOT, digest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload)
    published = preserve_prior_artifact(
        paths,
        source=paths.lock_path,
        root=LOCK_EVIDENCE_ROOT,
        digest=digest,
        label="prior lock",
    )
    assert Path(published) == dest
    assert dest.read_bytes() == payload


def _advance_ledger_only(store: dict[str, Any]) -> None:
    """Interrupt exactly between the receipt append and the lock publication.

    The interruption is installed in its own nested context, so undoing it leaves every
    synthetic constant the ``store`` fixture patched still in place.
    """
    paths = store["paths"]
    real_write = transition._write_authority

    def _interrupt(path: Path, document: Any) -> None:
        if path == paths.lock_path:
            raise RuntimeError("lock publication interrupted")
        real_write(path, document)

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(transition, "_write_authority", _interrupt)
        with pytest.raises(RuntimeError, match="lock publication interrupted"):
            apply_path_bound_transition(paths)
    # The outer fixture pins survive: only the write interruption was undone.
    assert transition._write_authority is real_write
    assert transition.TARGET_MODULE_SHA256 == store["pins"]["TARGET_MODULE_SHA256"]
    assert transition.PRIOR_LOCK_SHA256 == store["pins"]["PRIOR_LOCK_SHA256"]
    assert transition.PRIOR_AMENDMENT_LEDGER_SHA256 == (
        store["pins"]["PRIOR_AMENDMENT_LEDGER_SHA256"]
    )


def test_interruption_after_ledger_advance_is_recoverable(store: dict[str, Any]) -> None:
    paths = store["paths"]
    lock_before = paths.lock_path.read_bytes()
    _advance_ledger_only(store)
    # Receipt first: the ledger advanced, the lock did not.
    ledger = json.loads(paths.amendment_ledger_path.read_text())
    assert len(ledger["binding"]["source_receipts"]) == TARGET_RECEIPT_COUNT
    assert paths.lock_path.read_bytes() == lock_before
    assert preflight(paths).state == STATE_LEDGER_ADVANCED

    # Only this same transition finishes it, and it appends no second receipt.
    receipt = apply_path_bound_transition(paths)
    assert receipt["executed"] is True
    finished = json.loads(paths.amendment_ledger_path.read_text())
    assert finished["binding"]["source_receipts"] == ledger["binding"]["source_receipts"]
    assert preflight(paths).state == STATE_COMPLETE


def test_completed_transition_is_idempotent(store: dict[str, Any]) -> None:
    paths = store["paths"]
    first = apply_path_bound_transition(paths)
    surface = _surface(store["root"])
    second = apply_path_bound_transition(paths)
    assert second["executed"] is False
    assert second["state"] == STATE_COMPLETE
    # A completed store re-proves itself and changes nothing at all.
    assert _surface(store["root"]) == surface
    assert second["final"] == first["final"]
    assert second["target_source_identity"] == first["target_source_identity"]


def test_lock_advanced_before_its_receipt_authorizes_nothing(
    store: dict[str, Any]
) -> None:
    paths = store["paths"]
    ledger_bytes = paths.amendment_ledger_path.read_bytes()
    apply_path_bound_transition(paths)
    # Put the pinned ledger back beside the advanced lock.
    paths.amendment_ledger_path.write_bytes(ledger_bytes)
    with pytest.raises(TransitionError, match="authorizes nothing"):
        preflight(paths)


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        ("extra_receipt", "pinned transition identity"),
        ("rewritten_receipt", "not the reviewed transform"),
        ("altered_accounting", "pinned transition identity"),
        ("altered_evidence", "preserved_prior lock_sha256|pinned transition identity"),
        ("widened_lock", "changed more than the executing identity"),
    ],
)
def test_every_other_mixed_state_is_rejected(
    store: dict[str, Any], tamper: str, message: str
) -> None:
    paths = store["paths"]
    apply_path_bound_transition(paths)
    if tamper == "extra_receipt":
        document = json.loads(paths.amendment_ledger_path.read_text())
        receipts = document["binding"]["source_receipts"]
        receipts.append(dict(receipts[-1]))
        paths.amendment_ledger_path.write_bytes(canonical_json(document))
    elif tamper == "rewritten_receipt":
        document = json.loads(paths.amendment_ledger_path.read_text())
        document["binding"]["source_receipts"][0]["prepared_at"] = "1999-01-01T00:00:00+00:00"
        paths.amendment_ledger_path.write_bytes(canonical_json(document))
    elif tamper == "altered_accounting":
        document = json.loads(paths.amendment_ledger_path.read_text())
        key = next(iter(document["charges"]))
        document["charges"][key]["transferred_bytes"] = 1
        paths.amendment_ledger_path.write_bytes(canonical_json(document))
    elif tamper == "altered_evidence":
        preserved = paths.evidence(LOCK_EVIDENCE_ROOT, transition.PRIOR_LOCK_SHA256)
        preserved.write_bytes(b"{}\n")
    else:
        document = json.loads(paths.lock_path.read_text())
        document["retained_snapshot"] = {"widened": ["evidence"]}
        paths.lock_path.write_bytes(canonical_json(document))

    with pytest.raises(TransitionError, match=message):
        preflight(paths)


def test_receipt_reports_exact_identities_and_zero_sample_work(
    store: dict[str, Any]
) -> None:
    paths = store["paths"]
    receipt = apply_path_bound_transition(paths)
    assert receipt["prior"]["code_config_digest"] == transition.PRIOR_CODE_CONFIG_DIGEST
    assert receipt["prior"]["source_receipts"] == PRIOR_RECEIPT_COUNT
    assert receipt["final"]["code_config_digest"] == transition.TARGET_CODE_CONFIG_DIGEST
    assert receipt["final"]["source_receipts"] == TARGET_RECEIPT_COUNT
    assert receipt["final"]["lock_sha256"] == _sha256(paths.lock_path.read_bytes())
    assert receipt["final"]["amendment_ledger_sha256"] == _sha256(
        paths.amendment_ledger_path.read_bytes()
    )
    assert receipt["final"]["plan_digest"] == transition.PRIOR_PLAN_DIGEST
    assert receipt["final"]["plan_version"] == 4
    assert receipt["final"]["ledger_reservations"] == 0
    # Explicitly zero sample work, and no authority claimed.
    assert receipt["work"] == {
        "samples_acquired": 0,
        "reservations_reconciled": 0,
        "network_requests": 0,
        "credentials_read": 0,
        "reports_written": 0,
        "manifests_written": 0,
        "checkpoints_written": 0,
    }
    assert "authorizes no acquisition" in receipt["authorization"]


def test_no_network_credential_acquisition_or_reconciliation_path() -> None:
    source = Path(transition.__file__).read_text(encoding="utf-8")
    cli = Path(
        "scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "import httpx",
        "import requests",
        "import socket",
        "urllib.request",
        "COINALYZE_API_KEY",
        "api_key",
        "atomic_download",
        "fetch_bytes",
        "reconcile(",
        "run_source_qualification",
    ):
        assert forbidden not in source, forbidden
        assert forbidden not in cli, forbidden


def test_cli_exposes_no_authority_or_policy_override() -> None:
    import ast

    source = Path(
        "scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    options = [
        str(node.args[0].value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]
    assert options
    forbidden = (
        "identity",
        "digest",
        "receipt-count",
        "receipts",
        "scope",
        "recovery",
        "policy",
        "force",
        "state",
        "override",
    )
    for option in options:
        assert not any(word in option for word in forbidden), option
        # Locations only.
        assert option.endswith(("-path", "-root"))
    assert "apply_path_bound_transition(paths)" in source
    assert "return 0" in source


@pytest.mark.parametrize("pin", ["hash", "bytes"])
def test_wrong_uncompressed_manifest_pin_stops_before_any_mutation(
    store: dict[str, Any], monkeypatch: pytest.MonkeyPatch, pin: str
) -> None:
    if pin == "hash":
        monkeypatch.setattr(transition, "PRIOR_MANIFEST_UNCOMPRESSED_SHA256", "0" * 64)
        field = "manifest_uncompressed_sha256"
    else:
        monkeypatch.setattr(transition, "PRIOR_MANIFEST_UNCOMPRESSED_BYTES", 1)
        field = "manifest_uncompressed_bytes"
    before = _surface(store["root"])
    with pytest.raises(TransitionError, match="pinned transition identity") as exc:
        apply_path_bound_transition(store["paths"])
    assert exc.value.context["field"] == field
    # The expanded identity is proved before any evidence or authority is touched.
    assert _surface(store["root"]) == before


def test_uncompressed_manifest_identity_is_streamed(store: dict[str, Any]) -> None:
    import inspect

    digest, size = transition.prove_manifest_uncompressed_identity(
        store["paths"].manifest_detail_path
    )
    assert digest == _sha256(store["expanded"])
    assert size == len(store["expanded"])
    source = inspect.getsource(transition.prove_manifest_uncompressed_identity)
    # Bounded reads only: the expanded body is never materialized.
    assert "handle.read(" in source
    assert ".read()" not in source.replace("handle.read(1024 * 1024)", "")


def test_ledger_advanced_middle_state_is_reachable_and_classified(
    store: dict[str, Any]
) -> None:
    paths = store["paths"]
    lock_before = paths.lock_path.read_bytes()
    _advance_ledger_only(store)
    ledger = json.loads(paths.amendment_ledger_path.read_text())
    lock = json.loads(paths.lock_path.read_text())
    # The ledger legitimately carries three receipts while the pristine lock carries two;
    # an unconditional binding comparison would make this state impossible.
    assert len(ledger["binding"]["source_receipts"]) == TARGET_RECEIPT_COUNT
    assert (
        len(lock["budget_snapshot"]["amendment_binding"]["source_receipts"])
        == PRIOR_RECEIPT_COUNT
    )
    assert ledger["binding"] != lock["budget_snapshot"]["amendment_binding"]
    assert paths.lock_path.read_bytes() == lock_before
    assert preflight(paths).state == STATE_LEDGER_ADVANCED


def test_arbitrary_binding_mismatch_outside_the_branch_forms_is_rejected(
    store: dict[str, Any]
) -> None:
    paths = store["paths"]
    # Fresh state, but the lock binding does not match the pristine ledger binding.
    document = json.loads(paths.lock_path.read_text())
    binding = document["budget_snapshot"]["amendment_binding"]
    binding["allowance_id"] = "cex002_some_other_allowance"
    paths.lock_path.write_bytes(canonical_json(document))
    with pytest.raises(TransitionError):
        preflight(paths)


@pytest.mark.parametrize(
    "tamper",
    [
        "binding_field_mirrored",
        "extra_receipt_field",
        "legacy_state",
        "legacy_note",
        "envelope_field",
        "integrity_state_digest",
        "integrity_added_field",
    ],
)
def test_completed_ledger_may_not_widen_authority(
    store: dict[str, Any], tamper: str
) -> None:
    paths = store["paths"]
    apply_path_bound_transition(paths)
    ledger = json.loads(paths.amendment_ledger_path.read_text())
    lock = json.loads(paths.lock_path.read_text())

    if tamper == "binding_field_mirrored":
        # The dangerous case: widen a non-receipt binding field and mirror it into the
        # lock, so a prefix-only comparison would accept both.
        ledger["binding"]["download_authorized"] = True
        lock["budget_snapshot"]["amendment_binding"] = ledger["binding"]
        paths.lock_path.write_bytes(canonical_json(lock))
    elif tamper == "extra_receipt_field":
        ledger["binding"]["source_receipts"][-1]["operator_note"] = "approved"
        lock["budget_snapshot"]["amendment_binding"] = ledger["binding"]
        paths.lock_path.write_bytes(canonical_json(lock))
    elif tamper == "legacy_state":
        ledger["legacy_state"] = "unresolved"
    elif tamper == "legacy_note":
        ledger["legacy_note"] = "reclassified"
    elif tamper == "envelope_field":
        ledger["kind"] = "some_other_document"
    elif tamper == "integrity_state_digest":
        ledger["integrity"]["state_sha256"] = "0" * 64
    else:
        ledger["integrity"]["charge_count"] = 999

    paths.amendment_ledger_path.write_bytes(canonical_json(ledger))
    with pytest.raises(TransitionError, match="not the reviewed transform|receipt_fields"):
        preflight(paths)


def test_ledger_first_recovery_publishes_no_duplicate_receipt(
    store: dict[str, Any]
) -> None:
    paths = store["paths"]
    _advance_ledger_only(store)
    ledger_after_interrupt = paths.amendment_ledger_path.read_bytes()
    evidence_before = _surface(store["root"] / LEDGER_EVIDENCE_ROOT.split("/")[0])

    receipt = apply_path_bound_transition(paths)

    assert receipt["executed"] is True
    assert receipt["state"] == STATE_COMPLETE
    # The already-advanced ledger is untouched: recovery publishes the lock only.
    assert paths.amendment_ledger_path.read_bytes() == ledger_after_interrupt
    ledger = json.loads(paths.amendment_ledger_path.read_text())
    assert len(ledger["binding"]["source_receipts"]) == TARGET_RECEIPT_COUNT
    # Evidence is reused, never recreated from the advanced live files.
    assert _surface(store["root"] / LEDGER_EVIDENCE_ROOT.split("/")[0]) == evidence_before
    assert set(receipt["preserved_evidence"]) == {"report", "checkpoint", "lock", "ledger"}


def test_completed_execution_is_a_byte_for_byte_no_op(store: dict[str, Any]) -> None:
    paths = store["paths"]
    apply_path_bound_transition(paths)
    surface = _surface(store["root"])
    receipt = apply_path_bound_transition(paths)
    assert receipt["executed"] is False
    # A completed store re-proves its evidence and writes nothing at all.
    assert _surface(store["root"]) == surface


@pytest.mark.parametrize("name", ["report", "checkpoint", "lock", "ledger"])
@pytest.mark.parametrize("state", [STATE_LEDGER_ADVANCED, STATE_COMPLETE])
@pytest.mark.parametrize("damage", ["missing", "substituted", "symlinked"])
def test_advanced_states_reject_damaged_prior_evidence(
    store: dict[str, Any], name: str, state: str, damage: str
) -> None:
    paths = store["paths"]
    roots = {
        "report": (REPORT_EVIDENCE_ROOT, transition.PRIOR_REPORT_SHA256),
        "checkpoint": (CHECKPOINT_EVIDENCE_ROOT, transition.PRIOR_CHECKPOINT_SHA256),
        "lock": (LOCK_EVIDENCE_ROOT, transition.PRIOR_LOCK_SHA256),
        "ledger": (LEDGER_EVIDENCE_ROOT, transition.PRIOR_AMENDMENT_LEDGER_SHA256),
    }
    if state == STATE_LEDGER_ADVANCED:
        _advance_ledger_only(store)
    else:
        apply_path_bound_transition(paths)
    root, digest = roots[name]
    evidence = paths.evidence(root, digest)
    assert evidence.is_file()

    if damage == "missing":
        evidence.unlink()
    elif damage == "substituted":
        evidence.write_bytes(b'{"substituted": true}\n')
    else:
        elsewhere = store["root"] / f"{name}-elsewhere.json"
        elsewhere.write_bytes(evidence.read_bytes())
        evidence.unlink()
        evidence.symlink_to(elsewhere)

    before = _surface(store["root"])
    # The authority result itself must reject: an advanced state requires all four prior
    # evidence objects, not only the two its structural reconstruction reads.
    with pytest.raises(TransitionError):
        preflight(paths)
    assert _surface(store["root"]) == before
    # And the transaction boundary rejects too, immediately before its first write.
    with pytest.raises(TransitionError):
        apply_path_bound_transition(paths)
    # No further mutation on any rejection path.
    assert _surface(store["root"]) == before


def test_fresh_preflight_allows_absent_evidence(store: dict[str, Any]) -> None:
    paths = store["paths"]
    # Nothing is published yet, so a fresh store has no evidence objects at all.
    for _name, _source, root, digest, _label in transition._prior_artifact_plan(paths):
        assert not paths.evidence(root, digest).exists()
    assert preflight(paths).state == STATE_FRESH


def test_advanced_states_never_recreate_evidence_from_live_authority(
    store: dict[str, Any]
) -> None:
    paths = store["paths"]
    _advance_ledger_only(store)
    ledger_evidence = paths.evidence(
        LEDGER_EVIDENCE_ROOT, transition.PRIOR_AMENDMENT_LEDGER_SHA256
    )
    ledger_evidence.unlink()
    # The live ledger now carries three receipts; recreating evidence from it would both
    # succeed silently and record the wrong prior bytes. It must fail closed instead.
    with pytest.raises(TransitionError, match="preserved prior ledger is missing"):
        apply_path_bound_transition(paths)
    assert not ledger_evidence.exists()


def test_only_the_fresh_state_publishes_prior_evidence() -> None:
    import inspect

    source = inspect.getsource(transition.resolve_prior_artifacts)
    assert "STATE_FRESH" in source
    assert "publish_prior_artifacts" in source
    assert "require_prior_artifacts" in source
    # The verifying path reads no live authority file.
    verifier = inspect.getsource(transition.require_prior_artifacts)
    for forbidden in (
        "lock_path",
        "amendment_ledger_path",
        "report_path",
        "checkpoint_path",
    ):
        assert forbidden not in verifier
