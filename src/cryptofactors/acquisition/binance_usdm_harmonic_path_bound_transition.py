"""CEX-002 ADR-0022 — the reviewed path-bound source-authority transition.

The qualification source now refuses basename-only retained recovery unless the frozen
candidate domain binds a basename to exactly one full key. That correction changes the
executing module, and therefore the code/config identity the durable version-4 lock and
amendment ledger recorded. Ordinary execution must keep failing closed until this one
reviewed transition advances that identity.

It is deliberately narrow. It is pinned to one exact pre-state, changes exactly two
fields plus explicit transition metadata, preserves four prior artifacts content-
addressably before touching anything live, and does nothing else at all: no transport, no
credential, no network, no sample acquisition, no ledger reconciliation, and no write to
the report, manifest, checkpoint, listing state, metadata, cache, plan, or sizing tree.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    AMENDMENT_LEDGER_FILENAME,
    BUDGET_LEDGER_FILENAME,
    CONTRACT_METADATA_FILENAME,
    SAMPLE_PLAN_LOCK_FILENAME,
    compute_sha256,
    file_sha256,
)

TICKET_ID: str = "CEX-002"
TRANSITION_ID: str = "cex002_adr0022_path_bound_source_transition"
TRANSITION_SCHEMA_VERSION: str = "cex002_path_bound_transition_v1"

# --- pinned pre-state (review 208) ------------------------------------------------------

PRIOR_REPORT_SHA256: str = (
    "bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227"
)
PRIOR_REPORT_BYTES: int = 13_559_766
PRIOR_MANIFEST_SHA256: str = (
    "576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4"
)
PRIOR_MANIFEST_BYTES: int = 11_294_610
PRIOR_MANIFEST_UNCOMPRESSED_SHA256: str = (
    "1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d"
)
PRIOR_MANIFEST_UNCOMPRESSED_BYTES: int = 466_713_055
PRIOR_LOCK_SHA256: str = (
    "522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6"
)
PRIOR_LOCK_BYTES: int = 426_276
PRIOR_AMENDMENT_LEDGER_SHA256: str = (
    "259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0"
)
PRIOR_AMENDMENT_LEDGER_BYTES: int = 26_103
PRIOR_LEGACY_LEDGER_SHA256: str = (
    "47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6"
)
PRIOR_LEGACY_LEDGER_BYTES: int = 777
PRIOR_CHECKPOINT_SHA256: str = (
    "cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff"
)
PRIOR_CHECKPOINT_BYTES: int = 487_815
PRIOR_RETRY_JOURNAL_SHA256: str = (
    "a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24"
)
PRIOR_RETRY_JOURNAL_BYTES: int = 13_737
PRIOR_SAMPLE_PLAN_SHA256: str = (
    "02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18"
)
PRIOR_SAMPLE_PLAN_BYTES: int = 51_124
PRIOR_LISTING_CHECKPOINT_SHA256: str = (
    "d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a"
)
PRIOR_LISTING_CHECKPOINT_BYTES: int = 33_206_753
PRIOR_METADATA_SHA256: str = (
    "e520f0f072730f566d027342ddc7e09f7b690ab80e76acbd40756759f13add1f"
)
PRIOR_METADATA_BYTES: int = 99_357

PRIOR_PLAN_VERSION: int = 4
PRIOR_PLAN_DIGEST: str = (
    "2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef"
)
PRIOR_PLAN_ENTRIES: int = 106
PRIOR_HISTORY_ROWS: int = 3
PRIOR_CODE_CONFIG_DIGEST: str = (
    "da33197203e0c9651dc84f42e6e2ce26867339cebe4c68286a00639046c08258"
)
PRIOR_RECEIPT_COUNT: int = 2
PRIOR_LEDGER_CHARGES: int = 84
PRIOR_LEDGER_RESERVATIONS: int = 0
PRIOR_LEDGER_CHARGED_BYTES: int = 1_049_324

# --- pinned target identity -------------------------------------------------------------

TARGET_MODULE_SHA256: str = (
    "2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74"
)
TARGET_CODE_CONFIG_DIGEST: str = (
    "86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb"
)
TARGET_AUTHORITY_TABLE_VERSION: str = "review137-v1"
TARGET_DELIVERY_TABLE_SHA256: str = (
    "678d07e0679b0e116a372a333c3c33f74f5e421dadba393cb9516e56ae8b9a01"
)
TARGET_ALIAS_TABLE_SHA256: str = (
    "e9837ee2ac0711e41981e27979532be5095d61f04fb82442919c9f301f5998f8"
)
TARGET_RECEIPT_COUNT: int = PRIOR_RECEIPT_COUNT + 1

# --- evidence destinations ---------------------------------------------------------------

REPORT_EVIDENCE_ROOT: str = "evidence/prior_reports/sha256"
CHECKPOINT_EVIDENCE_ROOT: str = "evidence/checkpoints/sha256"
LOCK_EVIDENCE_ROOT: str = "evidence/locks/sha256"
LEDGER_EVIDENCE_ROOT: str = "evidence/ledgers/sha256"

STATE_FRESH: str = "pinned_pre_state_not_advanced"
STATE_LEDGER_ADVANCED: str = "ledger_advanced_lock_pending"
STATE_COMPLETE: str = "source_identity_advanced"

# The only lock fields this transition may change.
LOCK_TRANSFORM_FIELDS: frozenset[str] = frozenset({"inputs", "budget_snapshot"})
SNAPSHOT_TRANSFORM_FIELDS: frozenset[str] = frozenset(
    {"amendment_binding", "path_bound_transition"}
)


class TransitionError(RuntimeError):
    """A transition precondition failed. Nothing is preserved, changed, or published."""

    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


def _error(message: str, context: Mapping[str, Any]) -> TransitionError:
    return TransitionError(
        message, context={"transition": TRANSITION_ID, **dict(context)}
    )


def _require(condition: bool, message: str, context: Mapping[str, Any]) -> None:
    if not condition:
        raise _error(message, context)


def _exact(
    actual: Any, expected: Any, *, field_name: str, context: Mapping[str, Any]
) -> None:
    if actual != expected:
        raise _error(
            "pinned transition identity does not match",
            {**dict(context), "field": field_name, "actual": actual, "expected": expected},
        )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(payload: Mapping[str, Any]) -> bytes:
    """The one canonical serialization used for every durable byte this module writes."""
    return (json.dumps(dict(payload), indent=2, sort_keys=True) + "\n").encode("utf-8")


def target_source_identity() -> dict[str, str]:
    """The exact executing source identity this transition advances to."""
    return {
        "module_sha256": TARGET_MODULE_SHA256,
        "code_config_digest": TARGET_CODE_CONFIG_DIGEST,
        "reviewed_authority_table_version": TARGET_AUTHORITY_TABLE_VERSION,
        "delivery_table_sha256": TARGET_DELIVERY_TABLE_SHA256,
        "alias_table_sha256": TARGET_ALIAS_TABLE_SHA256,
    }


@dataclass(frozen=True, slots=True)
class TransitionPaths:
    """Where the pinned bytes live. Locations only; every identity is pinned."""

    store_root: Path
    report_path: Path
    manifest_detail_path: Path
    qualification_source_path: Path

    @property
    def lock_path(self) -> Path:
        return self.store_root / SAMPLE_PLAN_LOCK_FILENAME

    @property
    def amendment_ledger_path(self) -> Path:
        return self.store_root / AMENDMENT_LEDGER_FILENAME

    @property
    def legacy_ledger_path(self) -> Path:
        return self.store_root / BUDGET_LEDGER_FILENAME

    @property
    def checkpoint_path(self) -> Path:
        return self.store_root / "cex002_qualification_progress.json"

    @property
    def retry_journal_path(self) -> Path:
        return self.store_root / "cex002_retry_journal.json"

    @property
    def sample_plan_path(self) -> Path:
        return self.store_root / "cex002_sample_plan.json"

    @property
    def listing_checkpoint_path(self) -> Path:
        return self.store_root / "cex002_listing_checkpoint.json"

    @property
    def metadata_path(self) -> Path:
        return self.store_root / CONTRACT_METADATA_FILENAME

    def evidence(self, root: str, digest: str) -> Path:
        return self.store_root / root / f"{digest}.json"


def immutable_pinned_files(paths: TransitionPaths) -> tuple[tuple[Path, str, int, str], ...]:
    """Every pinned artifact this transition must never write."""
    return (
        (paths.report_path, PRIOR_REPORT_SHA256, PRIOR_REPORT_BYTES, "report"),
        (
            paths.manifest_detail_path,
            PRIOR_MANIFEST_SHA256,
            PRIOR_MANIFEST_BYTES,
            "manifest detail",
        ),
        (
            paths.legacy_ledger_path,
            PRIOR_LEGACY_LEDGER_SHA256,
            PRIOR_LEGACY_LEDGER_BYTES,
            "legacy ledger",
        ),
        (
            paths.checkpoint_path,
            PRIOR_CHECKPOINT_SHA256,
            PRIOR_CHECKPOINT_BYTES,
            "sample checkpoint",
        ),
        (
            paths.retry_journal_path,
            PRIOR_RETRY_JOURNAL_SHA256,
            PRIOR_RETRY_JOURNAL_BYTES,
            "retry journal",
        ),
        (
            paths.sample_plan_path,
            PRIOR_SAMPLE_PLAN_SHA256,
            PRIOR_SAMPLE_PLAN_BYTES,
            "sample plan",
        ),
        (
            paths.listing_checkpoint_path,
            PRIOR_LISTING_CHECKPOINT_SHA256,
            PRIOR_LISTING_CHECKPOINT_BYTES,
            "listing checkpoint",
        ),
        (paths.metadata_path, PRIOR_METADATA_SHA256, PRIOR_METADATA_BYTES, "official metadata"),
    )


# --- preflight ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TransitionAuthority:
    """The proved pre-state and where this store stands in the transaction."""

    paths: TransitionPaths
    lock: Mapping[str, Any]
    ledger: Mapping[str, Any]
    prior_receipts: tuple[Mapping[str, Any], ...]
    state: str


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    _require(path.is_file(), f"the pinned {label} is missing", {"path": str(path)})
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"the pinned {label} is not JSON", {"path": str(path)}) from exc
    _require(
        isinstance(document, dict),
        f"the pinned {label} is not an object",
        {"path": str(path)},
    )
    return dict(document)


def _receipts_of(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    binding = dict(document.get("binding") or {})
    receipts = binding.get("source_receipts")
    _require(
        isinstance(receipts, list), "the amendment binding has no source receipts", {}
    )
    return [dict(item) for item in receipts]  # type: ignore[union-attr]


def _read_no_follow(path: Path) -> bytes | None:
    """Read a real file only: a symlink at the path is refused, never followed."""
    try:
        handle = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _error(
            "a transition path is not a regular file",
            {"path": str(path), "errno": exc.errno},
        ) from exc
    with open(handle, "rb", closefd=True) as reader:
        return reader.read()


def prove_manifest_uncompressed_identity(path: Path) -> tuple[str, int]:
    """Stream-decompress the pinned gzip and prove its expanded identity.

    The expanded body is hundreds of megabytes, so it is never materialized: it is read
    in bounded chunks, hashed and counted as it goes, and discarded.
    """
    digest = hashlib.sha256()
    total = 0
    try:
        with gzip.open(path, "rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                total += len(chunk)
    except (OSError, EOFError, gzip.BadGzipFile) as exc:
        raise _error(
            "the pinned manifest detail is unreadable or truncated", {"path": str(path)}
        ) from exc
    return digest.hexdigest(), total


def preflight(paths: TransitionPaths) -> TransitionAuthority:
    """Prove the whole pinned pre-state before anything is preserved or changed.

    Fresh, ledger-advanced/lock-pending, and complete are each proved structurally. Every
    other mixed state - a lock advanced before its receipt, extra receipts, altered
    accounting, altered evidence - authorizes nothing.
    """
    context = {"store_root": str(paths.store_root)}
    _exact(
        file_sha256(paths.qualification_source_path),
        TARGET_MODULE_SHA256,
        field_name="qualification_source_sha256",
        context=context,
    )
    for path, digest, size, label in immutable_pinned_files(paths):
        _require(path.is_file(), f"the pinned {label} is missing", {"path": str(path)})
        _exact(
            file_sha256(path), digest, field_name=f"{label}_sha256", context=context
        )
        _exact(
            int(path.stat().st_size), size, field_name=f"{label}_bytes", context=context
        )
    # Review 208 pins both manifest identities, so the expanded body is proved too.
    expanded_digest, expanded_bytes = prove_manifest_uncompressed_identity(
        paths.manifest_detail_path
    )
    _exact(
        expanded_digest,
        PRIOR_MANIFEST_UNCOMPRESSED_SHA256,
        field_name="manifest_uncompressed_sha256",
        context=context,
    )
    _exact(
        expanded_bytes,
        PRIOR_MANIFEST_UNCOMPRESSED_BYTES,
        field_name="manifest_uncompressed_bytes",
        context=context,
    )

    lock = _load_json(paths.lock_path, label="version-4 lock")
    ledger = _load_json(paths.amendment_ledger_path, label="amendment ledger")
    _exact(
        lock.get("plan_version"),
        PRIOR_PLAN_VERSION,
        field_name="lock.plan_version",
        context=context,
    )
    _exact(
        lock.get("plan_digest"),
        PRIOR_PLAN_DIGEST,
        field_name="lock.plan_digest",
        context=context,
    )
    _exact(
        len(list((lock.get("plan") or {}).get("entries") or ())),
        PRIOR_PLAN_ENTRIES,
        field_name="lock.plan_entries",
        context=context,
    )
    _exact(
        len(list(lock.get("history") or ())),
        PRIOR_HISTORY_ROWS,
        field_name="lock.history_rows",
        context=context,
    )
    charges = dict(ledger.get("charges") or {})
    reservations = dict(ledger.get("reservations") or {})
    _exact(
        len(charges), PRIOR_LEDGER_CHARGES, field_name="ledger.charges", context=context
    )
    _exact(
        len(reservations),
        PRIOR_LEDGER_RESERVATIONS,
        field_name="ledger.reservations",
        context=context,
    )
    _exact(
        sum(int(row["transferred_bytes"]) for row in charges.values()),
        PRIOR_LEDGER_CHARGED_BYTES,
        field_name="ledger.transferred_bytes",
        context=context,
    )
    receipts = _receipts_of(ledger)
    lock_binding = dict(
        dict(lock.get("budget_snapshot") or {}).get("amendment_binding") or {}
    )
    # The lock and ledger bindings are compared per branch, never unconditionally: in the
    # one recoverable middle state the ledger legitimately carries three receipts while
    # the pristine lock still carries two.
    lock_digest = file_sha256(paths.lock_path)
    ledger_digest = file_sha256(paths.amendment_ledger_path)
    lock_pristine = lock_digest == PRIOR_LOCK_SHA256
    ledger_pristine = ledger_digest == PRIOR_AMENDMENT_LEDGER_SHA256
    executing = str(dict(lock.get("inputs") or {}).get("code_config_digest") or "")

    if lock_pristine and ledger_pristine:
        state = STATE_FRESH
        _exact(
            int(paths.lock_path.stat().st_size),
            PRIOR_LOCK_BYTES,
            field_name="lock_bytes",
            context=context,
        )
        _exact(
            int(paths.amendment_ledger_path.stat().st_size),
            PRIOR_AMENDMENT_LEDGER_BYTES,
            field_name="amendment_ledger_bytes",
            context=context,
        )
        _exact(
            len(receipts), PRIOR_RECEIPT_COUNT, field_name="receipt_count", context=context
        )
        _exact(
            executing,
            PRIOR_CODE_CONFIG_DIGEST,
            field_name="lock.code_config_digest",
            context=context,
        )
        # Fresh: the pristine lock carries the pristine two-receipt binding.
        _exact(
            lock_binding,
            dict(ledger.get("binding") or {}),
            field_name="fresh.lock_amendment_binding",
            context=context,
        )
        prior_receipts = tuple(receipts)
    elif lock_pristine:
        # The one recoverable middle: the receipt landed, the lock did not. The lock still
        # holds the preserved two-receipt binding; the ledger holds the fully proved
        # advanced one.
        state = STATE_LEDGER_ADVANCED
        prior_receipts, advanced_binding = _require_advanced_ledger(paths, receipts)
        preserved = _preserved_body(
            paths, LOCK_EVIDENCE_ROOT, PRIOR_LOCK_SHA256, label="prior lock"
        )
        _exact(
            lock_binding,
            dict(
                dict(preserved.get("budget_snapshot") or {}).get("amendment_binding") or {}
            ),
            field_name="pending.lock_amendment_binding",
            context=context,
        )
        assert advanced_binding is not None
        _exact(
            executing,
            PRIOR_CODE_CONFIG_DIGEST,
            field_name="lock.code_config_digest",
            context=context,
        )
    elif ledger_pristine:
        raise _error(
            "a lock advanced without its amendment receipt authorizes nothing", context
        )
    else:
        state = STATE_COMPLETE
        prior_receipts, advanced_binding = _require_advanced_ledger(paths, receipts)
        _exact(
            executing,
            TARGET_CODE_CONFIG_DIGEST,
            field_name="lock.code_config_digest",
            context=context,
        )
        # Complete: the lock carries exactly the fully proved advanced binding.
        _exact(
            lock_binding,
            dict(advanced_binding),
            field_name="complete.lock_amendment_binding",
            context=context,
        )
        _require_single_lock_transform(paths, lock=lock, ledger=ledger)
    if state != STATE_FRESH:
        # An advanced state must have all four prior evidence objects, not only the lock
        # and ledger its structural reconstruction happens to read. Fresh state is exempt
        # because publication has not happened yet. The transaction rechecks this
        # immediately before its first write; this is the authority-result contract.
        require_prior_artifacts(paths)
    return TransitionAuthority(
        paths=paths,
        lock=lock,
        ledger=ledger,
        prior_receipts=prior_receipts,
        state=state,
    )


def _preserved_body(
    paths: TransitionPaths, root: str, digest: str, *, label: str
) -> dict[str, Any]:
    """Rehash one preserved evidence object and return its parsed body."""
    path = paths.evidence(root, digest)
    body = _read_no_follow(path)
    _require(body is not None, f"the preserved {label} is missing", {"path": str(path)})
    assert body is not None
    actual = _sha256_bytes(body)
    _exact(
        actual, digest, field_name=f"preserved_{label}_sha256", context={"path": str(path)}
    )
    document = json.loads(body.decode("utf-8"))
    _require(
        isinstance(document, dict),
        f"the preserved {label} is not an object",
        {"path": str(path)},
    )
    return dict(document)


RECEIPT_FIELDS: frozenset[str] = frozenset({"prepared_at", "source_identity"})


def _require_advanced_ledger(
    paths: TransitionPaths, receipts: Sequence[Mapping[str, Any]]
) -> tuple[tuple[Mapping[str, Any], ...], Mapping[str, Any]]:
    """The live ledger must be the one and only expected advanced document.

    The reviewed transform is exactly: the preserved prior ledger, plus one appended
    receipt of the reviewed two-field shape naming the target identity, plus that
    receipt's recomputed integrity. Rather than spot-checking selected fields, the
    expected document is reconstructed from the preserved bytes and the appended
    receipt's own preparation time, and the complete live document must equal it. Every
    binding field, envelope field, accounting record, legacy field, and integrity field
    is therefore covered.
    """
    context = {"store_root": str(paths.store_root)}
    accepted = _preserved_body(
        paths, LEDGER_EVIDENCE_ROOT, PRIOR_AMENDMENT_LEDGER_SHA256, label="prior ledger"
    )
    prior = _receipts_of(accepted)
    _exact(
        len(prior), PRIOR_RECEIPT_COUNT, field_name="preserved_receipt_count", context=context
    )
    _exact(
        len(receipts), TARGET_RECEIPT_COUNT, field_name="receipt_count", context=context
    )
    appended = dict(receipts[-1])
    # The appended receipt must have exactly the reviewed shape before it is trusted to
    # parameterize the expected document.
    _exact(
        sorted(appended), sorted(RECEIPT_FIELDS), field_name="appended_receipt_fields",
        context=context,
    )
    _exact(
        dict(appended.get("source_identity") or {}),
        target_source_identity(),
        field_name="appended_source_identity",
        context=context,
    )
    prepared_at = appended.get("prepared_at")
    _require(
        isinstance(prepared_at, str) and bool(prepared_at),
        "the appended receipt has no preparation time",
        context,
    )
    expected = _advanced_ledger(accepted, now_iso=str(prepared_at))
    live = _load_json(paths.amendment_ledger_path, label="amendment ledger")
    if live != expected:
        raise _error(
            "the advanced amendment ledger is not the reviewed transform",
            {
                **context,
                "changed": sorted(
                    name
                    for name in set(expected) | set(live)
                    if expected.get(name) != live.get(name)
                ),
            },
        )
    return tuple(prior), dict(expected.get("binding") or {})


def _require_single_lock_transform(
    paths: TransitionPaths, *, lock: Mapping[str, Any], ledger: Mapping[str, Any]
) -> None:
    """The live lock is the preserved lock plus exactly the reviewed transform."""
    context = {"store_root": str(paths.store_root)}
    accepted = _preserved_body(
        paths, LOCK_EVIDENCE_ROOT, PRIOR_LOCK_SHA256, label="prior lock"
    )
    # The binding copied here is the one `_require_advanced_ledger` fully proved, never
    # whatever the live ledger happens to carry.
    _prior, proved_binding = _require_advanced_ledger(paths, _receipts_of(ledger))
    expected = {
        **dict(accepted),
        "inputs": {
            **dict(accepted.get("inputs") or {}),
            "code_config_digest": TARGET_CODE_CONFIG_DIGEST,
        },
        "budget_snapshot": {
            **dict(accepted.get("budget_snapshot") or {}),
            "amendment_binding": dict(proved_binding),
            "path_bound_transition": _transition_metadata(paths),
        },
    }
    if dict(lock) != expected:
        raise _error(
            "the transition changed more than the executing identity",
            {
                **context,
                "changed": sorted(
                    name
                    for name in set(expected) | set(lock)
                    if expected.get(name) != lock.get(name)
                ),
            },
        )
    # Plan content, digest, history, and retained snapshot are untouched by construction;
    # assert them explicitly so a future edit cannot quietly widen this transform.
    for field_name in ("plan", "plan_digest", "history", "retained_snapshot", "locked_at"):
        _exact(
            lock.get(field_name),
            accepted.get(field_name),
            field_name=f"lock.{field_name}",
            context=context,
        )


def _transition_metadata(paths: TransitionPaths) -> dict[str, Any]:
    """The explicit ADR-0022 transition and evidence record stored in the lock."""
    return {
        "transition_id": TRANSITION_ID,
        "schema_version": TRANSITION_SCHEMA_VERSION,
        "prior_code_config_digest": PRIOR_CODE_CONFIG_DIGEST,
        "target_code_config_digest": TARGET_CODE_CONFIG_DIGEST,
        "target_module_sha256": TARGET_MODULE_SHA256,
        "prior_report_evidence_path": str(
            paths.evidence(REPORT_EVIDENCE_ROOT, PRIOR_REPORT_SHA256)
        ),
        "prior_checkpoint_evidence_path": str(
            paths.evidence(CHECKPOINT_EVIDENCE_ROOT, PRIOR_CHECKPOINT_SHA256)
        ),
        "prior_lock_evidence_path": str(
            paths.evidence(LOCK_EVIDENCE_ROOT, PRIOR_LOCK_SHA256)
        ),
        "prior_ledger_evidence_path": str(
            paths.evidence(LEDGER_EVIDENCE_ROOT, PRIOR_AMENDMENT_LEDGER_SHA256)
        ),
        "manifest_detail_sha256": PRIOR_MANIFEST_SHA256,
        "download_authorized": False,
    }


# --- evidence preservation ----------------------------------------------------------------


def _fsync_directory(handle: int) -> None:
    os.fsync(handle)


def _open_directory_no_follow(path: Path) -> int:
    try:
        return os.open(str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise _error(
            "an evidence directory is not a real directory",
            {"path": str(path), "errno": exc.errno},
        ) from exc


def _publish_at(*, directory: int, name: str, payload: bytes, label: str) -> None:
    """Stage, link, fsync, and clean up entirely through one validated directory fd."""
    tmp_name = f".partial-{name}.{os.urandom(8).hex()}.tmp"
    handle_fd = os.open(
        tmp_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory,
    )
    try:
        with open(handle_fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # A link cannot replace a racing destination, so a concurrent nonidentical
            # publication is never overwritten.
            os.link(tmp_name, name, src_dir_fd=directory, dst_dir_fd=directory)
        except FileExistsError:
            existing_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            with open(existing_fd, "rb", closefd=True) as reader:
                if reader.read() != payload:
                    raise _error(
                        f"a different {label} already occupies its content address",
                        {"name": name},
                    ) from None
            return
        _fsync_directory(directory)
    finally:
        try:
            os.unlink(tmp_name, dir_fd=directory)
        except FileNotFoundError:
            pass


def preserve_prior_artifact(
    paths: TransitionPaths, *, source: Path, root: str, digest: str, label: str
) -> str:
    """Preserve one exact prior artifact at its own verified content address.

    Existing identical evidence is reused only after rehashing; a collision with
    different bytes fails closed rather than overwriting.
    """
    dest = paths.evidence(root, digest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = source.read_bytes()
    actual = _sha256_bytes(payload)
    _exact(actual, digest, field_name=f"{label}_sha256", context={"path": str(source)})
    directory = _open_directory_no_follow(dest.parent)
    try:
        _publish_at(directory=directory, name=dest.name, payload=payload, label=label)
    finally:
        os.close(directory)
    _exact(
        compute_sha256(dest),
        digest,
        field_name=f"preserved_{label}_sha256",
        context={"path": str(dest)},
    )
    return str(dest)


def _prior_artifact_plan(
    paths: TransitionPaths,
) -> tuple[tuple[str, Path, str, str, str], ...]:
    """The four prior artifacts: name, live source, evidence root, digest, and label."""
    return (
        ("report", paths.report_path, REPORT_EVIDENCE_ROOT, PRIOR_REPORT_SHA256, "prior report"),
        (
            "checkpoint",
            paths.checkpoint_path,
            CHECKPOINT_EVIDENCE_ROOT,
            PRIOR_CHECKPOINT_SHA256,
            "prior checkpoint",
        ),
        ("lock", paths.lock_path, LOCK_EVIDENCE_ROOT, PRIOR_LOCK_SHA256, "prior lock"),
        (
            "ledger",
            paths.amendment_ledger_path,
            LEDGER_EVIDENCE_ROOT,
            PRIOR_AMENDMENT_LEDGER_SHA256,
            "prior ledger",
        ),
    )


def publish_prior_artifacts(paths: TransitionPaths) -> dict[str, str]:
    """Publish the four prior artifacts from the live pinned pre-state.

    Only the fresh state may do this: it is the one state in which the live lock and
    ledger still *are* the prior bytes.
    """
    return {
        name: preserve_prior_artifact(
            paths, source=source, root=root, digest=digest, label=label
        )
        for name, source, root, digest, label in _prior_artifact_plan(paths)
    }


def require_prior_artifacts(paths: TransitionPaths) -> dict[str, str]:
    """Re-prove the four already-published prior artifacts, reading no live authority.

    After the ledger or lock has advanced, the live files are no longer the prior bytes,
    so evidence may only be verified - never recreated from them. A missing, substituted,
    symlinked, or nonidentical object fails before any further mutation.
    """
    resolved: dict[str, str] = {}
    for name, _source, root, digest, label in _prior_artifact_plan(paths):
        dest = paths.evidence(root, digest)
        body = _read_no_follow(dest)
        _require(
            body is not None,
            f"the preserved {label} is missing",
            {"path": str(dest), "name": name},
        )
        assert body is not None
        _exact(
            _sha256_bytes(body),
            digest,
            field_name=f"preserved_{name}_sha256",
            context={"path": str(dest)},
        )
        resolved[name] = str(dest)
    return resolved


def resolve_prior_artifacts(paths: TransitionPaths, *, state: str) -> dict[str, str]:
    """State-aware evidence handling: publish only when fresh, otherwise re-prove."""
    if state == STATE_FRESH:
        return publish_prior_artifacts(paths)
    return require_prior_artifacts(paths)


# --- the transaction ----------------------------------------------------------------------


def _write_authority(path: Path, document: Mapping[str, Any]) -> None:
    """Publish one live authority file atomically through a validated directory fd."""
    payload = canonical_json(document)
    directory = _open_directory_no_follow(path.parent)
    tmp_name = f".partial-{path.name}.{os.urandom(8).hex()}.tmp"
    try:
        handle_fd = os.open(
            tmp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        try:
            with open(handle_fd, "wb", closefd=True) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path.name, src_dir_fd=directory, dst_dir_fd=directory)
            _fsync_directory(directory)
        finally:
            try:
                os.unlink(tmp_name, dir_fd=directory)
            except FileNotFoundError:
                pass
    finally:
        os.close(directory)


def _advanced_ledger(ledger: Mapping[str, Any], *, now_iso: str) -> dict[str, Any]:
    """The ledger with exactly one appended receipt and a recomputed integrity summary."""
    binding = dict(ledger.get("binding") or {})
    receipts = [dict(item) for item in (binding.get("source_receipts") or ())]
    receipts.append({"prepared_at": now_iso, "source_identity": target_source_identity()})
    advanced = {
        **dict(ledger),
        "binding": {**binding, "source_receipts": receipts},
    }
    integrity = dict(advanced.get("integrity") or {})
    if integrity:
        state = dict(
            budget_bytes=advanced.get("budget_bytes"),
            charges={
                key: [
                    int(row["planned_bytes"]),
                    int(row["transferred_bytes"]),
                    str(row["disposition"]),
                    str(row["sha256"]),
                ]
                for key, row in sorted(dict(advanced.get("charges") or {}).items())
            },
            reservations={
                key: int(row["planned_bytes"])
                for key, row in sorted(dict(advanced.get("reservations") or {}).items())
            },
            legacy_max_bytes=advanced.get("legacy_max_bytes"),
            legacy_state=advanced.get("legacy_state"),
            binding=advanced["binding"],
        )
        blob = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
        integrity["state_sha256"] = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        advanced["integrity"] = integrity
    return advanced


def _advanced_lock(
    lock: Mapping[str, Any], *, ledger: Mapping[str, Any], paths: TransitionPaths
) -> dict[str, Any]:
    """The lock with only its executing identity, binding, and transition metadata set."""
    return {
        **dict(lock),
        "inputs": {
            **dict(lock.get("inputs") or {}),
            "code_config_digest": TARGET_CODE_CONFIG_DIGEST,
        },
        "budget_snapshot": {
            **dict(lock.get("budget_snapshot") or {}),
            "amendment_binding": dict(ledger.get("binding") or {}),
            "path_bound_transition": _transition_metadata(paths),
        },
    }


def apply_path_bound_transition(
    paths: TransitionPaths, *, now: datetime | None = None
) -> dict[str, Any]:
    """Preserve, advance the receipt, then advance the lock. Nothing else at all.

    Receipt first and lock last, so an interruption leaves the one recoverable middle
    state that only this same transition may finish. A completed store re-proves itself
    and changes nothing.
    """
    now_iso = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
    authority = preflight(paths)
    # Evidence is published only from the pinned pre-state; an advanced store re-proves
    # what already exists rather than preserving mutated authority as "prior".
    evidence = resolve_prior_artifacts(paths, state=authority.state)
    executed = False
    if authority.state != STATE_COMPLETE:
        ledger = dict(authority.ledger)
        if authority.state == STATE_FRESH:
            # 1. the amendment receipt advances first.
            ledger = _advanced_ledger(ledger, now_iso=now_iso)
            _write_authority(paths.amendment_ledger_path, ledger)
        else:
            ledger = _load_json(paths.amendment_ledger_path, label="amendment ledger")
        # 2. the matching lock identity, binding, and metadata are published last.
        _write_authority(
            paths.lock_path,
            _advanced_lock(authority.lock, ledger=ledger, paths=paths),
        )
        executed = True
    final = preflight(paths)
    _exact(
        final.state, STATE_COMPLETE, field_name="final_state", context={"executed": executed}
    )
    final_ledger = _load_json(paths.amendment_ledger_path, label="amendment ledger")
    final_lock = _load_json(paths.lock_path, label="version-4 lock")
    return build_receipt(
        paths,
        executed=executed,
        prior_receipts=final.prior_receipts,
        lock=final_lock,
        ledger=final_ledger,
        evidence=evidence,
        generated_at=now_iso,
    )


def build_receipt(
    paths: TransitionPaths,
    *,
    executed: bool,
    prior_receipts: Sequence[Mapping[str, Any]],
    lock: Mapping[str, Any],
    ledger: Mapping[str, Any],
    evidence: Mapping[str, str],
    generated_at: str,
) -> dict[str, Any]:
    """Exact prior and final identities, and an explicit record of zero sample work."""
    receipts = _receipts_of(ledger)
    return {
        "schema_version": TRANSITION_SCHEMA_VERSION,
        "ticket": TICKET_ID,
        "transition_id": TRANSITION_ID,
        "generated_at": generated_at,
        "executed": executed,
        "state": STATE_COMPLETE,
        "prior": {
            "report_sha256": PRIOR_REPORT_SHA256,
            "manifest_detail_sha256": PRIOR_MANIFEST_SHA256,
            "lock_sha256": PRIOR_LOCK_SHA256,
            "amendment_ledger_sha256": PRIOR_AMENDMENT_LEDGER_SHA256,
            "legacy_ledger_sha256": PRIOR_LEGACY_LEDGER_SHA256,
            "checkpoint_sha256": PRIOR_CHECKPOINT_SHA256,
            "code_config_digest": PRIOR_CODE_CONFIG_DIGEST,
            "source_receipts": len(prior_receipts),
        },
        "final": {
            "lock_sha256": file_sha256(paths.lock_path),
            "amendment_ledger_sha256": file_sha256(paths.amendment_ledger_path),
            "code_config_digest": str(
                dict(lock.get("inputs") or {}).get("code_config_digest") or ""
            ),
            "source_receipts": len(receipts),
            "plan_version": lock.get("plan_version"),
            "plan_digest": lock.get("plan_digest"),
            "plan_entries": len(list((lock.get("plan") or {}).get("entries") or ())),
            "history_rows": len(list(lock.get("history") or ())),
            "ledger_charges": len(dict(ledger.get("charges") or {})),
            "ledger_reservations": len(dict(ledger.get("reservations") or {})),
        },
        "target_source_identity": target_source_identity(),
        "preserved_evidence": dict(evidence),
        "immutable": {
            label: digest for _path, digest, _size, label in immutable_pinned_files(paths)
        },
        "work": {
            "samples_acquired": 0,
            "reservations_reconciled": 0,
            "network_requests": 0,
            "credentials_read": 0,
            "reports_written": 0,
            "manifests_written": 0,
            "checkpoints_written": 0,
        },
        "authorization": (
            "this transition advances only the executing source identity: it authorizes "
            "no acquisition, accepts no gate, and changes no ticket state"
        ),
    }
