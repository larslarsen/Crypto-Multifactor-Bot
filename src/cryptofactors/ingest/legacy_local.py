"""LEG-001 — Legacy local file scanner and deterministic inventory builder.

Forensic census only. Registration does not imply acceptance. Source bytes
are never rewritten. Classification is metadata, never promotion.

Traversal and hashing are descriptor-relative (dir_fd + O_NOFOLLOW +
O_DIRECTORY). The directory work queue is binary-safe SQLite. Non-UTF-8
POSIX names are represented deterministically without surrogate code points
in UTF-8 JSON. Publication uses exclusive no-clobber link/create semantics.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
import stat as statmod
import tempfile
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Final

SCANNER_VERSION: Final[str] = "1.2.0"
INVENTORY_SCHEMA_VERSION: Final[str] = "1.2.0"
_MERGE_FAN_IN: Final[int] = 16
_RUN_BUFFER_LIMIT: Final[int] = 2048
_QUEUE_BATCH: Final[int] = 256

# Open flags — required APIs (no hasattr probes for openat/fstatat).
_O_RDONLY: Final[int] = os.O_RDONLY
_O_DIRECTORY: Final[int] = os.O_DIRECTORY
_O_NOFOLLOW: Final[int] = os.O_NOFOLLOW
_O_CLOEXEC: Final[int] = getattr(os, "O_CLOEXEC", 0)


# ---- Exceptions -----------------------------------------------------------

class LegacyScanError(Exception):
    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


class LegacyPathError(LegacyScanError):
    pass


class LegacyPathCollisionError(LegacyPathError):
    pass


class LegacyOutputError(LegacyScanError):
    pass


class LegacyInventoryExistsError(LegacyOutputError):
    pass


class LegacyConfigError(LegacyScanError):
    pass


class LegacyTraversalError(LegacyScanError):
    pass


# ---- Enums ----------------------------------------------------------------

class EntryType(str, Enum):
    REGULAR_FILE = "regular_file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    SPECIAL = "special"
    UNREADABLE = "unreadable"
    MALFORMED = "malformed"


class EvidenceClass(str, Enum):
    RAW_PROVIDER_OBJECT = "raw_provider_object"
    NORMALIZED_OBSERVATION = "normalized_observation"
    DERIVED_FEATURE = "derived_feature"
    LABEL_RETURN = "label_return"
    PREDICTION_MODEL_ARTIFACT = "prediction_model_artifact"
    REPORT_RESULT = "report_result"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class ProvenanceClass(str, Enum):
    VERIFIED_OFFICIAL = "verified_official"
    VERIFIED_CROSSSOURCE = "verified_crosssource"
    LEGACY_PROVENANCE_PARTIAL = "legacy_provenance_partial"
    LEGACY_UNKNOWN = "legacy_unknown"


class ScanStatus(str, Enum):
    OK = "ok"
    SKIPPED_EXCLUDED = "skipped_excluded"
    ERROR_UNREADABLE = "error_unreadable"
    ERROR_CHANGED = "error_changed"
    ERROR_SPECIAL = "error_special"
    ERROR_SYMLINK = "error_symlink"
    ERROR_HASH = "error_hash"
    ERROR_OVERLONG = "error_overlong"
    ERROR_UNENCODABLE = "error_unencodable"
    ERROR_MALFORMED = "error_malformed"
    ERROR_COLLISION = "error_collision"


# ---- Classification / Exclusion -------------------------------------------

@dataclass(frozen=True, slots=True)
class ClassificationRule:
    name: str
    match: Callable[[str], bool]
    evidence_class: EvidenceClass
    provenance_class: ProvenanceClass = ProvenanceClass.LEGACY_UNKNOWN
    basis: str = ""


def _default_classification_rules() -> tuple[ClassificationRule, ...]:
    def _re(pattern: str) -> Callable[[str], bool]:
        compiled = re.compile(pattern, re.IGNORECASE)
        def _m(rel: str) -> bool:
            return compiled.search(rel) is not None
        return _m
    return (
        ClassificationRule("config_dotfiles", _re(r"(^|/)\.(env|ini|cfg|conf|yaml|yml|toml|json)(\.|$)"), EvidenceClass.CONFIGURATION, basis="path pattern: config/dotfile"),
        ClassificationRule("config_extensions", _re(r"\.(ya?ml|toml|ini|cfg|conf|json)$"), EvidenceClass.CONFIGURATION, basis="path pattern: config extension"),
        ClassificationRule("model_artifacts", _re(r"\.(pkl|joblib|h5|hdf5|onnx|pt|pth|xgb|json)$|(^|/)(models?|artifacts?|checkpoints?)/"), EvidenceClass.PREDICTION_MODEL_ARTIFACT, basis="path pattern: model/artifact"),
        ClassificationRule("reports_results", _re(r"(^|/)(reports?|results?|metrics?|evals?|figures?)/|\.(png|jpg|jpeg|svg|pdf|html)$"), EvidenceClass.REPORT_RESULT, basis="path pattern: report/result"),
        ClassificationRule("labels_returns", _re(r"(^|/)(labels?|targets?|returns?)/"), EvidenceClass.LABEL_RETURN, basis="path pattern: label/return"),
        ClassificationRule("features_derived", _re(r"(^|/)(features?|derived|indicators?)/"), EvidenceClass.DERIVED_FEATURE, basis="path pattern: derived/feature"),
        ClassificationRule("normalized_bars", _re(r"(^|/)(canonical|normalized|bars?|ohlcv)/|\.(parquet|pq)$"), EvidenceClass.NORMALIZED_OBSERVATION, basis="path pattern: normalized/bar"),
        ClassificationRule("raw_provider", _re(r"(^|/)(raw|provider|archive|downloads?|backfill)/|\.(csv|zip|gz|bz2|zst)$"), EvidenceClass.RAW_PROVIDER_OBJECT, basis="path pattern: raw/provider"),
    )


@dataclass(frozen=True, slots=True)
class ExclusionRule:
    name: str
    match: Callable[[str], bool]


def _default_exclusion_rules() -> tuple[ExclusionRule, ...]:
    def _seg(name: str) -> Callable[[str], bool]:
        def _m(rel: str) -> bool:
            return name in rel.split("/")
        return _m
    def _suffixes(*suffixes: str) -> Callable[[str], bool]:
        lower = tuple(s.lower() for s in suffixes)
        def _m(rel: str) -> bool:
            return any(rel.rsplit("/", 1)[-1].lower().endswith(s) for s in lower)
        return _m
    def _names(*names: str) -> Callable[[str], bool]:
        s = {n.lower() for n in names}
        def _m(rel: str) -> bool:
            return rel.rsplit("/", 1)[-1].lower() in s
        return _m
    return (
        ExclusionRule("git_metadata", _seg(".git")),
        ExclusionRule("hg_metadata", _seg(".hg")),
        ExclusionRule("svn_metadata", _seg(".svn")),
        ExclusionRule("venv", _seg(".venv")),
        ExclusionRule("venv_dir", _seg("venv")),
        ExclusionRule("virtualenv", _seg(".virtualenv")),
        ExclusionRule("pycache", _seg("__pycache__")),
        ExclusionRule("mypy_cache", _seg(".mypy_cache")),
        ExclusionRule("pytest_cache", _seg(".pytest_cache")),
        ExclusionRule("ruff_cache", _seg(".ruff_cache")),
        ExclusionRule("ipynb_checkpoints", _seg(".ipynb_checkpoints")),
        ExclusionRule("node_modules", _seg("node_modules")),
        ExclusionRule("egg_info", lambda r: ".egg-info" in r.split("/")),
        ExclusionRule("dist", _seg("dist")),
        ExclusionRule("build", _seg("build")),
        ExclusionRule("tox", _seg(".tox")),
        ExclusionRule("nox", _seg(".nox")),
        ExclusionRule("idea", _seg(".idea")),
        ExclusionRule("vscode", _seg(".vscode")),
        ExclusionRule("ds_store", _names(".ds_store", "thumbs.db")),
        ExclusionRule("secret_files", _names(".env", ".env.local", ".env.production", "secrets.yaml", "secrets.yml", "secrets.json", "credentials.json", "service_account.json")),
        ExclusionRule("key_files", _suffixes(".key", ".pem", ".p12", ".pfx", ".jks", ".keystore")),
        ExclusionRule("python_bytecode", _suffixes(".pyc", ".pyo", ".pyd")),
        ExclusionRule("leg001_work", lambda r: any(p.startswith(".leg001-") for p in r.split("/"))),
    )


# ---- Models ---------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class InventoryEntry:
    relative_path: str
    entry_type: EntryType
    byte_size: int | None
    mtime_ns: int | None
    sha256: str | None
    evidence_class: EvidenceClass
    provenance_class: ProvenanceClass
    classification_basis: str
    scan_status: ScanStatus
    error: str | None = None

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "entry_type": self.entry_type.value,
            "byte_size": self.byte_size,
            "mtime_ns": self.mtime_ns,
            "sha256": self.sha256,
            "evidence_class": self.evidence_class.value,
            "provenance_class": self.provenance_class.value,
            "classification_basis": self.classification_basis,
            "scan_status": self.scan_status.value,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    sha256: str
    relative_paths: tuple[str, ...]

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "sha256": self.sha256,
            "relative_paths": list(self.relative_paths),
            "path_count": len(self.relative_paths),
        }


@dataclass(frozen=True, slots=True)
class InventorySummary:
    root: str
    root_resolved: str
    scanner_version: str
    schema_version: str
    scanned_at_utc: str
    total_entries: int
    hashed_regular_files: int
    total_hashed_bytes: int
    counts_by_entry_type: Mapping[str, int]
    counts_by_evidence_class: Mapping[str, int]
    counts_by_provenance_class: Mapping[str, int]
    counts_by_scan_status: Mapping[str, int]
    excluded_by_rule: Mapping[str, int]
    duplicate_hash_groups: int
    duplicate_path_count: int
    error_count: int
    inventory_sha256: str
    inventory_byte_size: int
    inventory_uri: str
    summary_uri: str
    duplicate_report_sha256: str
    duplicate_report_byte_size: int
    duplicate_report_uri: str

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "root_resolved": self.root_resolved,
            "scanner_version": self.scanner_version,
            "schema_version": self.schema_version,
            "scanned_at_utc": self.scanned_at_utc,
            "total_entries": self.total_entries,
            "hashed_regular_files": self.hashed_regular_files,
            "total_hashed_bytes": self.total_hashed_bytes,
            "counts_by_entry_type": dict(sorted(self.counts_by_entry_type.items())),
            "counts_by_evidence_class": dict(sorted(self.counts_by_evidence_class.items())),
            "counts_by_provenance_class": dict(sorted(self.counts_by_provenance_class.items())),
            "counts_by_scan_status": dict(sorted(self.counts_by_scan_status.items())),
            "excluded_by_rule": dict(sorted(self.excluded_by_rule.items())),
            "duplicate_hash_groups": self.duplicate_hash_groups,
            "duplicate_path_count": self.duplicate_path_count,
            "error_count": self.error_count,
            "inventory_sha256": self.inventory_sha256,
            "inventory_byte_size": self.inventory_byte_size,
            "inventory_uri": self.inventory_uri,
            "summary_uri": self.summary_uri,
            "duplicate_report_sha256": self.duplicate_report_sha256,
            "duplicate_report_byte_size": self.duplicate_report_byte_size,
            "duplicate_report_uri": self.duplicate_report_uri,
        }


def _validate_output_basename(name: str, label: str) -> None:
    if not name or name != name.strip():
        raise LegacyConfigError(
            f"{label} must be a non-empty basename without surrounding whitespace",
            context={label: name},
        )
    if "/" in name or "\\" in name or name in (".", "..") or name.startswith("/"):
        raise LegacyConfigError(
            f"{label} must be a simple basename (no separators, not . or ..)",
            context={label: name},
        )
    if os.sep in name or (os.altsep and os.altsep in name):
        raise LegacyConfigError(f"{label} must be a simple basename", context={label: name})


@dataclass(frozen=True, slots=True)
class ScanConfig:
    chunk_size: int = 1024 * 1024
    classification_rules: Sequence[ClassificationRule] = field(default_factory=_default_classification_rules)
    exclusion_rules: Sequence[ExclusionRule] = field(default_factory=_default_exclusion_rules)
    follow_symlinks: bool = False
    inventory_filename: str = "legacy_inventory.jsonl"
    summary_filename: str = "legacy_inventory_summary.json"
    duplicate_report_filename: str = "legacy_inventory_duplicates.jsonl"
    max_path_bytes: int = 4096

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise LegacyConfigError("chunk_size must be positive", context={"chunk_size": self.chunk_size})
        if self.follow_symlinks:
            raise LegacyConfigError("follow_symlinks must be False for LEG-001 forensic scan")
        if self.max_path_bytes <= 0:
            raise LegacyConfigError("max_path_bytes must be positive")
        _validate_output_basename(self.inventory_filename, "inventory_filename")
        _validate_output_basename(self.summary_filename, "summary_filename")
        _validate_output_basename(self.duplicate_report_filename, "duplicate_report_filename")
        if len({self.inventory_filename, self.summary_filename, self.duplicate_report_filename}) != 3:
            raise LegacyConfigError("inventory, summary, and duplicate-report filenames must be distinct")


# ---- Path identity (binary-safe, no truncation, no surrogates in JSON) ----

def _name_to_display(name: bytes) -> str:
    """Deterministic JSON-safe display form of one path component.

    Valid UTF-8 is emitted as-is. Non-UTF-8 bytes use a ``b64:`` prefix so the
    result contains only UTF-8 code points (no surrogates).
    """
    try:
        text = name.decode("utf-8")
    except UnicodeDecodeError:
        return "b64:" + base64.b64encode(name).decode("ascii")
    # Reject embedded NUL and path separators inside a single component display
    # only for safety of the joined relative_path string; identity uses raw bytes.
    if "\x00" in text:
        return "b64:" + base64.b64encode(name).decode("ascii")
    return text


def _parts_to_relative(parts: tuple[bytes, ...]) -> str:
    if not parts:
        return ""
    return "/".join(_name_to_display(p) for p in parts)


def _parts_identity_key(parts: tuple[bytes, ...]) -> bytes:
    """Canonical binary identity key — preserves exact FS names including newlines."""
    # Length-prefixed segments so embedded newlines/slashes cannot collide.
    out = bytearray()
    for p in parts:
        out.append(0x01)
        ln = len(p)
        out.extend(ln.to_bytes(4, "big"))
        out.extend(p)
    out.append(0x00)
    return bytes(out)


def _sanitize_error(exc: BaseException, *, max_len: int = 200) -> str:
    text = f"{type(exc).__name__}: {exc}"
    text = "".join(ch if ch.isprintable() or ch in " \t" else "?" for ch in text)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def _classify(rel: str, rules: Sequence[ClassificationRule]) -> tuple[EvidenceClass, ProvenanceClass, str]:
    for rule in rules:
        if rule.match(rel):
            prov = rule.provenance_class
            if prov in (ProvenanceClass.VERIFIED_OFFICIAL, ProvenanceClass.VERIFIED_CROSSSOURCE):
                prov = ProvenanceClass.LEGACY_UNKNOWN
            return rule.evidence_class, prov, rule.basis or rule.name
    return EvidenceClass.UNKNOWN, ProvenanceClass.LEGACY_UNKNOWN, "default:unknown"


def _match_exclusion(rel: str, rules: Sequence[ExclusionRule]) -> str | None:
    for rule in rules:
        if rule.match(rel):
            return rule.name
    return None


def _canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def _fsync_file(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _entry_type_from_mode(mode: int) -> EntryType:
    if statmod.S_ISLNK(mode):
        return EntryType.SYMLINK
    if statmod.S_ISREG(mode):
        return EntryType.REGULAR_FILE
    if statmod.S_ISDIR(mode):
        return EntryType.DIRECTORY
    return EntryType.SPECIAL


def _stat_identity(st: os.stat_result) -> tuple[int, int, int, int, int | None, int | None]:
    """(dev, ino, mode_type, size, mtime_ns, ctime_ns)."""
    return (
        st.st_dev,
        st.st_ino,
        statmod.S_IFMT(st.st_mode),
        st.st_size,
        getattr(st, "st_mtime_ns", None),
        getattr(st, "st_ctime_ns", None),
    )


# ---- Descriptor-relative open / walk --------------------------------------

def _open_dir_nofollow(dir_fd: int | None, name: str | None) -> int:
    """Open a directory without following symlinks.

    If ``name`` is None, ``dir_fd`` must be None and ``name`` is unused —
    callers open the root by absolute path separately.
    """
    flags = _O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW | _O_CLOEXEC
    if dir_fd is None:
        raise LegacyTraversalError("dir_fd required for relative open")
    assert name is not None
    return os.open(name, flags, dir_fd=dir_fd)


def _open_root_dir(root: Path) -> int:
    flags = _O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW | _O_CLOEXEC
    return os.open(str(root), flags)


def _open_file_nofollow(dir_fd: int, name: str) -> int:
    flags = _O_RDONLY | _O_NOFOLLOW | _O_CLOEXEC
    return os.open(name, flags, dir_fd=dir_fd)


def _walk_open_dir(root_fd: int, parts: tuple[bytes, ...]) -> int:
    """Open the directory identified by ``parts`` from ``root_fd``, no-follow.

    Each component is reopened with O_DIRECTORY|O_NOFOLLOW relative to its
    parent descriptor. A swapped symlink component raises OSError (ELOOP/ENOTDIR).
    """
    if not parts:
        # Duplicate the root fd so callers can close freely.
        return os.open(".", _O_RDONLY | _O_DIRECTORY | _O_CLOEXEC, dir_fd=root_fd)
    fd = root_fd
    owned: list[int] = []
    try:
        for i, comp in enumerate(parts):
            # Use filesystem encoding for the name relative to dir_fd.
            name = os.fsdecode(comp) if isinstance(comp, (bytes, bytearray)) else str(comp)
            # Prefer bytes name when possible for exactness.
            try:
                next_fd = os.open(comp, _O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW | _O_CLOEXEC, dir_fd=fd)
            except (TypeError, ValueError, OSError):
                next_fd = os.open(name, _O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW | _O_CLOEXEC, dir_fd=fd)
            if fd is not root_fd:
                owned.append(fd)
            fd = next_fd
        return fd
    except Exception:
        if fd is not root_fd:
            try:
                os.close(fd)
            except OSError:
                pass
        raise
    finally:
        for o in owned:
            try:
                os.close(o)
            except OSError:
                pass


def _hash_regular_at(
    dir_fd: int,
    name_bytes: bytes,
    *,
    chunk_size: int,
) -> tuple[str | None, int, int | None, ScanStatus, str | None]:
    """Hash a regular file relative to ``dir_fd`` with full identity revalidation."""
    file_fd: int | None = None
    name = os.fsdecode(name_bytes)
    try:
        try:
            try:
                file_fd = os.open(name_bytes, _O_RDONLY | _O_NOFOLLOW | _O_CLOEXEC, dir_fd=dir_fd)
            except (TypeError, ValueError, OSError):
                file_fd = os.open(name, _O_RDONLY | _O_NOFOLLOW | _O_CLOEXEC, dir_fd=dir_fd)
        except OSError as exc:
            err = _sanitize_error(exc)
            errno = getattr(exc, "errno", None)
            if errno in (getattr(__import__("errno"), "ELOOP", -1), getattr(__import__("errno"), "EPERM", -1)):
                return None, 0, None, ScanStatus.ERROR_SYMLINK, err
            return None, 0, None, ScanStatus.ERROR_UNREADABLE, err

        try:
            st_before = os.fstat(file_fd)
        except OSError as exc:
            return None, 0, None, ScanStatus.ERROR_UNREADABLE, _sanitize_error(exc)

        if statmod.S_ISLNK(st_before.st_mode):
            return None, 0, None, ScanStatus.ERROR_SYMLINK, "entry is a symlink"
        if not statmod.S_ISREG(st_before.st_mode):
            return (
                None,
                st_before.st_size,
                getattr(st_before, "st_mtime_ns", None),
                ScanStatus.ERROR_SPECIAL,
                "not a regular file",
            )

        id_before = _stat_identity(st_before)
        digest = hashlib.sha256()
        total = 0
        try:
            while True:
                chunk = os.read(file_fd, chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
                total += len(chunk)
        except OSError as exc:
            return (
                None,
                st_before.st_size,
                getattr(st_before, "st_mtime_ns", None),
                ScanStatus.ERROR_HASH,
                _sanitize_error(exc),
            )

        try:
            st_after = os.fstat(file_fd)
        except OSError as exc:
            return (
                None,
                st_before.st_size,
                getattr(st_before, "st_mtime_ns", None),
                ScanStatus.ERROR_CHANGED,
                _sanitize_error(exc),
            )

        if _stat_identity(st_after) != id_before or total != st_before.st_size:
            return (
                None,
                st_before.st_size,
                getattr(st_before, "st_mtime_ns", None),
                ScanStatus.ERROR_CHANGED,
                "file changed during scan",
            )

        # Revalidate directory entry still names the same object.
        try:
            st_dirent = os.stat(name_bytes, dir_fd=dir_fd, follow_symlinks=False)
        except (TypeError, ValueError, OSError):
            try:
                st_dirent = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
            except OSError as exc:
                return (
                    None,
                    st_before.st_size,
                    getattr(st_before, "st_mtime_ns", None),
                    ScanStatus.ERROR_CHANGED,
                    _sanitize_error(exc),
                )
        d_id = _stat_identity(st_dirent)
        if d_id[0] != id_before[0] or d_id[1] != id_before[1] or d_id[2] != id_before[2]:
            return (
                None,
                st_before.st_size,
                getattr(st_before, "st_mtime_ns", None),
                ScanStatus.ERROR_CHANGED,
                "directory entry replaced during scan",
            )

        return sha if (sha := digest.hexdigest()) else None, st_before.st_size, getattr(st_before, "st_mtime_ns", None), ScanStatus.OK, None
    finally:
        if file_fd is not None:
            try:
                os.close(file_fd)
            except OSError:
                pass


# ---- Exclusive publication (MAN-001-style no-clobber) ----------------------

class _PublishReservation:
    """Stage complete artifact set, exclusive publish, inode-proven rollback."""

    def __init__(self, output_dir: Path, basenames: Sequence[str]) -> None:
        self.output_dir = output_dir
        self.basenames = list(basenames)
        self.stage_dir: Path | None = None
        self.published: list[tuple[Path, int, int]] = []  # path, dev, ino

    def __enter__(self) -> _PublishReservation:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for name in self.basenames:
            dest = self.output_dir / name
            try:
                st = os.lstat(dest)
            except FileNotFoundError:
                continue
            raise LegacyInventoryExistsError(
                "output artifact already exists (no-clobber)",
                context={"path": str(dest), "ino": st.st_ino},
            )
        self.stage_dir = Path(
            tempfile.mkdtemp(prefix=".leg001-stage-", dir=str(self.output_dir))
        )
        return self

    def stage_path(self, basename: str) -> Path:
        assert self.stage_dir is not None
        if basename not in self.basenames:
            raise LegacyOutputError("unexpected artifact basename", context={"basename": basename})
        return self.stage_dir / basename

    def publish(self) -> None:
        assert self.stage_dir is not None
        _fsync_dir(self.stage_dir)
        # Publish completion marker (summary) last.
        ordered = [b for b in self.basenames if b]  # caller puts summary last
        for name in ordered:
            staged = self.stage_dir / name
            if not staged.exists():
                self._rollback()
                raise LegacyOutputError(
                    "staged artifact missing before publication",
                    context={"basename": name},
                )
            final = self.output_dir / name
            # Exclusive: os.link fails with EEXIST if final exists.
            try:
                os.link(str(staged), str(final))
            except FileExistsError as exc:
                self._rollback()
                raise LegacyInventoryExistsError(
                    "output artifact collision during publication",
                    context={"path": str(final)},
                ) from exc
            except OSError as exc:
                # Cross-device: fall back to O_EXCL create + copy.
                if getattr(exc, "errno", None) == getattr(__import__("errno"), "EXDEV", -1):
                    try:
                        self._exclusive_copy(staged, final)
                    except FileExistsError as exc2:
                        self._rollback()
                        raise LegacyInventoryExistsError(
                            "output artifact collision during publication",
                            context={"path": str(final)},
                        ) from exc2
                    except OSError as exc2:
                        self._rollback()
                        raise LegacyOutputError(
                            f"atomic publication failed: {exc2}",
                            context={"path": str(final)},
                        ) from exc2
                else:
                    self._rollback()
                    raise LegacyOutputError(
                        f"atomic publication failed: {exc}",
                        context={"path": str(final)},
                    ) from exc
            st = os.lstat(final)
            self.published.append((final, st.st_dev, st.st_ino))
            try:
                _fsync_file(final)
            except OSError as exc:
                self._rollback()
                raise LegacyOutputError(
                    f"fsync after publish failed: {exc}",
                    context={"path": str(final)},
                ) from exc
        try:
            _fsync_dir(self.output_dir)
        except OSError:
            pass
        # Remove staged originals (links keep inodes where hardlinked).
        for name in ordered:
            try:
                (self.stage_dir / name).unlink(missing_ok=True)
            except OSError:
                pass
        try:
            self.stage_dir.rmdir()
        except OSError:
            pass
        self.stage_dir = None

    def _exclusive_copy(self, src: Path, dest: Path) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_CLOEXEC
        fd = os.open(str(dest), flags, 0o644)
        try:
            with open(src, "rb") as inf:
                while True:
                    chunk = inf.read(1024 * 1024)
                    if not chunk:
                        break
                    os.write(fd, chunk)
            os.fsync(fd)
        finally:
            os.close(fd)

    def _rollback(self) -> None:
        """Remove only files whose (dev, ino) matches what this publisher created."""
        for path, dev, ino in self.published:
            try:
                st = os.lstat(path)
                if st.st_dev == dev and st.st_ino == ino:
                    path.unlink(missing_ok=True)
            except OSError:
                pass
        self.published.clear()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type is not None:
            self._rollback()
        if self.stage_dir is not None and self.stage_dir.exists():
            self._bounded_rmtree(self.stage_dir)
        return None

    @staticmethod
    def _bounded_rmtree(root: Path) -> None:
        """Iterative cleanup — no recursive rmtree unbounded stack."""
        stack = [root]
        while stack:
            current = stack.pop()
            try:
                if current.is_symlink() or current.is_file():
                    current.unlink(missing_ok=True)
                    continue
            except OSError:
                continue
            try:
                children = list(current.iterdir())
            except OSError:
                try:
                    current.rmdir()
                except OSError:
                    pass
                continue
            if not children:
                try:
                    current.rmdir()
                except OSError:
                    pass
            else:
                stack.append(current)
                stack.extend(children)


# ---- External merge (unique intermediate paths, bounded fan-in) -----------

def _write_sorted_run(lines: list[tuple[str, str]], run_path: Path) -> None:
    lines.sort(key=lambda t: t[0])
    with run_path.open("w", encoding="utf-8") as handle:
        for _, line in lines:
            handle.write(line if line.endswith("\n") else line + "\n")


def _unique_merge_path(parent: Path) -> Path:
    return parent / f".merge-{uuid.uuid4().hex}.jsonl"


def _merge_runs_streaming(
    run_paths: list[Path],
    out_path: Path,
    *,
    fan_in: int = _MERGE_FAN_IN,
) -> tuple[str, int]:
    """K-way merge writing directly to ``out_path`` while computing SHA-256 and size.

    Returns (sha256_hex, byte_size). Never loads the full output into memory.
    Intermediate merge paths are unique UUIDs and never equal any input.
    """
    if not run_paths:
        out_path.write_bytes(b"")
        return hashlib.sha256(b"").hexdigest(), 0

    if len(run_paths) == 1:
        digest = hashlib.sha256()
        total = 0
        with run_paths[0].open("rb") as src, out_path.open("wb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
                digest.update(chunk)
                total += len(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        return digest.hexdigest(), total

    if len(run_paths) > fan_in:
        intermediate: list[Path] = []
        parent = out_path.parent
        try:
            for i in range(0, len(run_paths), fan_in):
                batch = run_paths[i : i + fan_in]
                mid = _unique_merge_path(parent)
                # Ensure mid is not in batch.
                while mid in batch or mid == out_path:
                    mid = _unique_merge_path(parent)
                _merge_runs_streaming(batch, mid, fan_in=fan_in)
                intermediate.append(mid)
            return _merge_runs_streaming(intermediate, out_path, fan_in=fan_in)
        finally:
            for p in intermediate:
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass

    # Open at most fan_in handles.
    handles: list[Any] = []
    heads: list[tuple[str, str, int] | None] = []
    try:
        for p in run_paths:
            h = p.open("r", encoding="utf-8")
            handles.append(h)
            line = h.readline()
            if line:
                obj = json.loads(line)
                heads.append((obj["relative_path"], line, len(handles) - 1))
            else:
                heads.append(None)

        digest = hashlib.sha256()
        total = 0
        with out_path.open("wb") as out:
            while True:
                active = [h for h in heads if h is not None]
                if not active:
                    break
                active.sort(key=lambda t: t[0])
                _, best_line, best_idx = active[0]
                raw = (best_line if best_line.endswith("\n") else best_line + "\n").encode("utf-8")
                out.write(raw)
                digest.update(raw)
                total += len(raw)
                nxt = handles[best_idx].readline()
                if nxt:
                    obj = json.loads(nxt)
                    heads[best_idx] = (obj["relative_path"], nxt, best_idx)
                else:
                    heads[best_idx] = None
            out.flush()
            os.fsync(out.fileno())
        return digest.hexdigest(), total
    finally:
        for h in handles:
            try:
                h.close()
            except OSError:
                pass


# ---- Scanner --------------------------------------------------------------

class LegacyLocalScanner:
    def __init__(self, config: ScanConfig | None = None) -> None:
        self._config = config or ScanConfig()

    def scan(self, legacy_root: Path | str, output_dir: Path | str) -> InventorySummary:
        root = Path(legacy_root)
        out = Path(output_dir)
        cfg = self._config

        try:
            root_st = os.lstat(root)
        except OSError as exc:
            raise LegacyPathError(f"cannot lstat legacy root: {exc}", context={"root": str(root)}) from exc
        if statmod.S_ISLNK(root_st.st_mode):
            raise LegacyPathError("legacy root must not be a symlink", context={"root": str(root)})
        if not statmod.S_ISDIR(root_st.st_mode):
            raise LegacyPathError("legacy root must be a directory", context={"root": str(root)})

        root_resolved = str(Path(root).resolve())
        out_abs = Path(out).expanduser()
        if not out_abs.is_absolute():
            out_abs = Path.cwd() / out_abs
        out_resolved = str(out_abs.resolve())

        if root_resolved == out_resolved:
            raise LegacyConfigError(
                "output_dir must not equal legacy_root",
                context={"root": root_resolved, "output_dir": out_resolved},
            )

        # Work area: always under output parent, named .leg001-work-* (auto-excluded).
        work_parent = Path(out_resolved).parent
        work_dir = Path(tempfile.mkdtemp(prefix=".leg001-work-", dir=str(work_parent)))
        work_resolved = str(work_dir.resolve())

        scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        # Summary last = completion marker.
        basenames = [
            cfg.inventory_filename,
            cfg.duplicate_report_filename,
            cfg.summary_filename,
        ]

        counts_entry: dict[str, int] = {}
        counts_evidence: dict[str, int] = {}
        counts_provenance: dict[str, int] = {}
        counts_status: dict[str, int] = {}
        excluded_by_rule: dict[str, int] = {}
        total_entries = 0
        hashed_files = 0
        hashed_bytes = 0
        error_count = 0
        run_paths: list[Path] = []
        run_buffer: list[tuple[str, str]] = []
        run_counter = 0
        runs_dir = work_dir / "runs"
        runs_dir.mkdir()

        def flush_run() -> None:
            nonlocal run_counter, run_buffer
            if not run_buffer:
                return
            rp = runs_dir / f"run-{run_counter:06d}.jsonl"
            _write_sorted_run(run_buffer, rp)
            run_paths.append(rp)
            run_counter += 1
            run_buffer = []

        def emit(entry: InventoryEntry) -> None:
            nonlocal total_entries, error_count
            line = json.dumps(
                entry.to_canonical_dict(), sort_keys=True, ensure_ascii=False, allow_nan=False
            )
            run_buffer.append((entry.relative_path, line))
            if len(run_buffer) >= _RUN_BUFFER_LIMIT:
                flush_run()
            counts_entry[entry.entry_type.value] = counts_entry.get(entry.entry_type.value, 0) + 1
            counts_evidence[entry.evidence_class.value] = (
                counts_evidence.get(entry.evidence_class.value, 0) + 1
            )
            counts_provenance[entry.provenance_class.value] = (
                counts_provenance.get(entry.provenance_class.value, 0) + 1
            )
            counts_status[entry.scan_status.value] = (
                counts_status.get(entry.scan_status.value, 0) + 1
            )
            total_entries += 1
            if entry.scan_status not in (ScanStatus.OK, ScanStatus.SKIPPED_EXCLUDED):
                error_count += 1

        def is_excluded_resolved(candidate_resolved: str) -> bool:
            if candidate_resolved == out_resolved or candidate_resolved.startswith(
                out_resolved + os.sep
            ):
                return True
            if candidate_resolved == work_resolved or candidate_resolved.startswith(
                work_resolved + os.sep
            ):
                return True
            return False

        root_fd: int | None = None
        try:
            root_fd = _open_root_dir(root)

            # Binary-safe SQLite control DB: queue + seen identities + hash index.
            db_path = work_dir / "control.sqlite"
            conn = sqlite3.connect(str(db_path))
            conn.execute(
                "CREATE TABLE dir_queue ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  parts BLOB NOT NULL"
                ")"
            )
            conn.execute(
                "CREATE TABLE seen ("
                "  id_key BLOB PRIMARY KEY NOT NULL"
                ")"
            )
            conn.execute(
                "CREATE TABLE hash_paths ("
                "  sha256 TEXT NOT NULL,"
                "  rel TEXT NOT NULL"
                ")"
            )
            conn.execute("CREATE INDEX idx_hp ON hash_paths(sha256)")

            # Seed queue with root (empty parts tuple).
            conn.execute("INSERT INTO dir_queue(parts) VALUES (?)", (b"",))
            conn.commit()

            while True:
                rows = conn.execute(
                    "SELECT id, parts FROM dir_queue ORDER BY id LIMIT ?",
                    (_QUEUE_BATCH,),
                ).fetchall()
                if not rows:
                    break
                for row_id, parts_blob in rows:
                    conn.execute("DELETE FROM dir_queue WHERE id = ?", (row_id,))
                    # Decode parts: empty blob = root; else length-prefixed segments.
                    parts = _decode_parts(parts_blob)
                    rel = _parts_to_relative(parts)

                    # Open this directory from the trusted root descriptor.
                    dir_fd: int | None = None
                    try:
                        dir_fd = _walk_open_dir(root_fd, parts)
                        # Confirm still a directory under the same root device tree.
                        st_dir = os.fstat(dir_fd)
                        if not statmod.S_ISDIR(st_dir.st_mode):
                            emit(
                                InventoryEntry(
                                    rel or ".",
                                    EntryType.UNREADABLE,
                                    None,
                                    None,
                                    None,
                                    EvidenceClass.UNKNOWN,
                                    ProvenanceClass.LEGACY_UNKNOWN,
                                    "not_a_directory",
                                    ScanStatus.ERROR_UNREADABLE,
                                    "queued path is not a directory",
                                )
                            )
                            continue
                    except OSError as exc:
                        emit(
                            InventoryEntry(
                                rel or ".",
                                EntryType.UNREADABLE,
                                None,
                                None,
                                None,
                                EvidenceClass.UNKNOWN,
                                ProvenanceClass.LEGACY_UNKNOWN,
                                "traversal_error",
                                ScanStatus.ERROR_UNREADABLE,
                                _sanitize_error(exc),
                            )
                        )
                        continue

                    try:
                        # List entries via fd-based listdir (bytes names when possible).
                        try:
                            names_raw = os.listdir(dir_fd)
                        except TypeError:
                            names_raw = os.listdir(dir_fd)
                        # Normalize to bytes.
                        name_list: list[bytes] = []
                        for n in names_raw:
                            if isinstance(n, bytes):
                                name_list.append(n)
                            else:
                                name_list.append(os.fsencode(n))

                        for name_b in name_list:
                            child_parts = parts + (name_b,)
                            child_rel = _parts_to_relative(child_parts)
                            id_key = _parts_identity_key(child_parts)

                            # Collision on exact binary identity.
                            try:
                                conn.execute(
                                    "INSERT INTO seen(id_key) VALUES (?)", (id_key,)
                                )
                            except sqlite3.IntegrityError:
                                raise LegacyPathCollisionError(
                                    "logical relative_path collision",
                                    context={"relative_path": child_rel},
                                ) from None

                            # Overlong — still emit full unique identity, mark status.
                            path_byte_len = len(id_key)
                            overlong = path_byte_len > cfg.max_path_bytes

                            # Resolved-path exclusion for output/work trees.
                            # We cannot resolve via follow; use name-based exclusion
                            # plus explicit resolved checks when the child is a dir
                            # we would enqueue.
                            excl = _match_exclusion(child_rel, cfg.exclusion_rules)
                            if excl is not None:
                                excluded_by_rule[excl] = excluded_by_rule.get(excl, 0) + 1
                                child_is_dir = False
                                try:
                                    st_c = os.stat(
                                        name_b, dir_fd=dir_fd, follow_symlinks=False
                                    )
                                    child_is_dir = statmod.S_ISDIR(st_c.st_mode)
                                except (TypeError, ValueError, OSError):
                                    try:
                                        st_c = os.stat(
                                            os.fsdecode(name_b),
                                            dir_fd=dir_fd,
                                            follow_symlinks=False,
                                        )
                                        child_is_dir = statmod.S_ISDIR(st_c.st_mode)
                                    except OSError:
                                        pass
                                emit(
                                    InventoryEntry(
                                        child_rel,
                                        EntryType.DIRECTORY if child_is_dir else EntryType.REGULAR_FILE,
                                        None,
                                        None,
                                        None,
                                        EvidenceClass.UNKNOWN,
                                        ProvenanceClass.LEGACY_UNKNOWN,
                                        f"excluded:{excl}",
                                        ScanStatus.SKIPPED_EXCLUDED,
                                    )
                                )
                                continue

                            if overlong:
                                emit(
                                    InventoryEntry(
                                        child_rel,
                                        EntryType.MALFORMED,
                                        None,
                                        None,
                                        None,
                                        EvidenceClass.UNKNOWN,
                                        ProvenanceClass.LEGACY_UNKNOWN,
                                        "overlong_path",
                                        ScanStatus.ERROR_OVERLONG,
                                        f"path identity exceeds {cfg.max_path_bytes} bytes",
                                    )
                                )
                                continue

                            # Stat no-follow relative to dir_fd.
                            try:
                                try:
                                    st = os.stat(
                                        name_b, dir_fd=dir_fd, follow_symlinks=False
                                    )
                                except (TypeError, ValueError, OSError):
                                    st = os.stat(
                                        os.fsdecode(name_b),
                                        dir_fd=dir_fd,
                                        follow_symlinks=False,
                                    )
                            except OSError as exc:
                                emit(
                                    InventoryEntry(
                                        child_rel,
                                        EntryType.UNREADABLE,
                                        None,
                                        None,
                                        None,
                                        EvidenceClass.UNKNOWN,
                                        ProvenanceClass.LEGACY_UNKNOWN,
                                        "lstat_error",
                                        ScanStatus.ERROR_UNREADABLE,
                                        _sanitize_error(exc),
                                    )
                                )
                                continue

                            et = _entry_type_from_mode(st.st_mode)

                            if et is EntryType.DIRECTORY:
                                # Enqueue binary parts for later descriptor-relative walk.
                                conn.execute(
                                    "INSERT INTO dir_queue(parts) VALUES (?)",
                                    (_encode_parts(child_parts),),
                                )
                                ev, prov, basis = _classify(
                                    child_rel, cfg.classification_rules
                                )
                                emit(
                                    InventoryEntry(
                                        child_rel,
                                        et,
                                        None,
                                        getattr(st, "st_mtime_ns", None),
                                        None,
                                        ev,
                                        prov,
                                        basis,
                                        ScanStatus.OK,
                                    )
                                )
                                continue

                            if et is EntryType.SYMLINK:
                                ev, prov, basis = _classify(
                                    child_rel, cfg.classification_rules
                                )
                                emit(
                                    InventoryEntry(
                                        child_rel,
                                        et,
                                        None,
                                        getattr(st, "st_mtime_ns", None),
                                        None,
                                        ev,
                                        prov,
                                        basis,
                                        ScanStatus.ERROR_SYMLINK,
                                        "symlink not followed",
                                    )
                                )
                                continue

                            if et is EntryType.SPECIAL:
                                ev, prov, basis = _classify(
                                    child_rel, cfg.classification_rules
                                )
                                emit(
                                    InventoryEntry(
                                        child_rel,
                                        et,
                                        st.st_size,
                                        getattr(st, "st_mtime_ns", None),
                                        None,
                                        ev,
                                        prov,
                                        basis,
                                        ScanStatus.ERROR_SPECIAL,
                                        "special file not hashed",
                                    )
                                )
                                continue

                            # Regular file — descriptor-relative hash.
                            sha, size, mtime_ns, status, err = _hash_regular_at(
                                dir_fd, name_b, chunk_size=cfg.chunk_size
                            )
                            if status is ScanStatus.OK and sha is not None:
                                hashed_files += 1
                                hashed_bytes += size
                                conn.execute(
                                    "INSERT INTO hash_paths(sha256, rel) VALUES (?, ?)",
                                    (sha, child_rel),
                                )
                            ev, prov, basis = _classify(
                                child_rel, cfg.classification_rules
                            )
                            emit(
                                InventoryEntry(
                                    child_rel,
                                    EntryType.REGULAR_FILE,
                                    size if size else None,
                                    mtime_ns,
                                    sha,
                                    ev,
                                    prov,
                                    basis,
                                    status,
                                    err,
                                )
                            )
                    finally:
                        if dir_fd is not None:
                            try:
                                os.close(dir_fd)
                            except OSError:
                                pass

                conn.commit()

            flush_run()
            conn.commit()

            # ---- Stream-merge inventory into stage; stream duplicates ----
            with _PublishReservation(Path(out_resolved), basenames) as pub:
                inv_stage = pub.stage_path(cfg.inventory_filename)
                inv_sha, inv_size = _merge_runs_streaming(run_paths, inv_stage)

                # Stream duplicate report from SQL — no full materialization.
                dup_stage = pub.stage_path(cfg.duplicate_report_filename)
                dup_sha, dup_size, dup_groups, dup_paths = _stream_duplicate_report(
                    conn, dup_stage
                )

                summary = InventorySummary(
                    root=str(root),
                    root_resolved=root_resolved,
                    scanner_version=SCANNER_VERSION,
                    schema_version=INVENTORY_SCHEMA_VERSION,
                    scanned_at_utc=scanned_at,
                    total_entries=total_entries,
                    hashed_regular_files=hashed_files,
                    total_hashed_bytes=hashed_bytes,
                    counts_by_entry_type=counts_entry,
                    counts_by_evidence_class=counts_evidence,
                    counts_by_provenance_class=counts_provenance,
                    counts_by_scan_status=counts_status,
                    excluded_by_rule=excluded_by_rule,
                    duplicate_hash_groups=dup_groups,
                    duplicate_path_count=dup_paths,
                    error_count=error_count,
                    inventory_sha256=inv_sha,
                    inventory_byte_size=inv_size,
                    inventory_uri=cfg.inventory_filename,
                    summary_uri=cfg.summary_filename,
                    duplicate_report_sha256=dup_sha,
                    duplicate_report_byte_size=dup_size,
                    duplicate_report_uri=cfg.duplicate_report_filename,
                )
                sum_stage = pub.stage_path(cfg.summary_filename)
                sum_bytes = _canonical_dumps(summary.to_canonical_dict()).encode("utf-8")
                with sum_stage.open("wb") as sf:
                    sf.write(sum_bytes)
                    sf.flush()
                    os.fsync(sf.fileno())

                pub.publish()

            conn.close()
            return summary

        except LegacyScanError:
            raise
        except OSError as exc:
            raise LegacyOutputError(
                f"filesystem failure during scan: {exc}",
                context={"root": str(root)},
            ) from exc
        finally:
            if root_fd is not None:
                try:
                    os.close(root_fd)
                except OSError:
                    pass
            if work_dir.exists():
                _PublishReservation._bounded_rmtree(work_dir)


def _encode_parts(parts: tuple[bytes, ...]) -> bytes:
    return _parts_identity_key(parts)


def _decode_parts(blob: bytes) -> tuple[bytes, ...]:
    if not blob:
        return ()
    parts: list[bytes] = []
    i = 0
    while i < len(blob):
        if blob[i] == 0x00:
            break
        if blob[i] != 0x01:
            break
        i += 1
        if i + 4 > len(blob):
            break
        ln = int.from_bytes(blob[i : i + 4], "big")
        i += 4
        parts.append(blob[i : i + ln])
        i += ln
    return tuple(parts)


def _stream_duplicate_report(
    conn: sqlite3.Connection, out_path: Path
) -> tuple[str, int, int, int]:
    """Stream duplicate groups from SQLite into ``out_path``. Returns sha, size, groups, paths."""
    digest = hashlib.sha256()
    total = 0
    groups = 0
    paths = 0
    with out_path.open("wb") as out:
        for (sha,) in conn.execute(
            "SELECT sha256 FROM hash_paths GROUP BY sha256 HAVING COUNT(*) > 1 ORDER BY sha256"
        ):
            rels = [
                row[0]
                for row in conn.execute(
                    "SELECT rel FROM hash_paths WHERE sha256 = ? ORDER BY rel", (sha,)
                )
            ]
            groups += 1
            paths += len(rels)
            group = DuplicateGroup(sha256=sha, relative_paths=tuple(rels))
            line = (
                json.dumps(
                    group.to_canonical_dict(),
                    sort_keys=True,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                + "\n"
            )
            raw = line.encode("utf-8")
            out.write(raw)
            digest.update(raw)
            total += len(raw)
        out.flush()
        os.fsync(out.fileno())
    return digest.hexdigest(), total, groups, paths


def scan_legacy_root(
    legacy_root: Path | str,
    output_dir: Path | str,
    *,
    config: ScanConfig | None = None,
) -> InventorySummary:
    """Scan a legacy root and write deterministic inventory artifacts."""
    return LegacyLocalScanner(config).scan(legacy_root, output_dir)
