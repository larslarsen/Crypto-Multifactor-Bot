"""LEG-001 — Legacy local file scanner and deterministic inventory builder.

Forensic census only. Registration does not imply acceptance. Source bytes
are never rewritten. Classification is metadata, never promotion.

Path identity is preserved exactly (no whitespace trimming, no backslash
reinterpretation on POSIX). Traversal/hashing use descriptor-relative,
no-follow operations where supported so a TOCTOU symlink replacement cannot
redirect the scanner outside the legacy root.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sqlite3
import stat as statmod
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Final

SCANNER_VERSION: Final[str] = "1.1.0"
INVENTORY_SCHEMA_VERSION: Final[str] = "1.1.0"
_MERGE_FAN_IN: Final[int] = 16
_QUEUE_BATCH: Final[int] = 256
_RUN_BUFFER_LIMIT: Final[int] = 2048


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
    )


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
        return {"sha256": self.sha256, "relative_paths": list(self.relative_paths), "path_count": len(self.relative_paths)}


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
            "root": self.root, "root_resolved": self.root_resolved,
            "scanner_version": self.scanner_version, "schema_version": self.schema_version,
            "scanned_at_utc": self.scanned_at_utc, "total_entries": self.total_entries,
            "hashed_regular_files": self.hashed_regular_files, "total_hashed_bytes": self.total_hashed_bytes,
            "counts_by_entry_type": dict(sorted(self.counts_by_entry_type.items())),
            "counts_by_evidence_class": dict(sorted(self.counts_by_evidence_class.items())),
            "counts_by_provenance_class": dict(sorted(self.counts_by_provenance_class.items())),
            "counts_by_scan_status": dict(sorted(self.counts_by_scan_status.items())),
            "excluded_by_rule": dict(sorted(self.excluded_by_rule.items())),
            "duplicate_hash_groups": self.duplicate_hash_groups, "duplicate_path_count": self.duplicate_path_count,
            "error_count": self.error_count, "inventory_sha256": self.inventory_sha256,
            "inventory_byte_size": self.inventory_byte_size, "inventory_uri": self.inventory_uri,
            "summary_uri": self.summary_uri, "duplicate_report_sha256": self.duplicate_report_sha256,
            "duplicate_report_byte_size": self.duplicate_report_byte_size, "duplicate_report_uri": self.duplicate_report_uri,
        }


def _validate_output_basename(name: str, label: str) -> None:
    if not name or name != name.strip():
        raise LegacyConfigError(f"{label} must be a non-empty basename without surrounding whitespace", context={label: name})
    if "/" in name or "\\" in name or name in (".", "..") or name.startswith("/"):
        raise LegacyConfigError(f"{label} must be a simple basename (no separators, not . or ..)", context={label: name})
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


def _join_rel(parent_rel: str, name: str) -> str:
    """Join parent relative path with exact filesystem name. No strip, no backslash rewrite."""
    if not parent_rel:
        return name
    return parent_rel + "/" + name


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


def _stat_identity(st: os.stat_result) -> tuple[int, int, int, int, int | None]:
    return (st.st_dev, st.st_ino, statmod.S_IFMT(st.st_mode), st.st_size, getattr(st, "st_mtime_ns", None))


def _hash_open_fd(fd: int, *, chunk_size: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    while True:
        chunk = os.read(fd, chunk_size)
        if not chunk:
            break
        digest.update(chunk)
        total += len(chunk)
    return digest.hexdigest(), total


def _hash_regular_nofollow(
    parent_path: Path, name: str, *, chunk_size: int
) -> tuple[str | None, int, int | None, ScanStatus, str | None]:
    """Hash a regular file with TOCTOU protection via O_NOFOLLOW + fstat identity checks."""
    dir_fd: int | None = None
    file_fd: int | None = None
    try:
        dir_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            dir_flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            dir_flags |= os.O_NOFOLLOW
        try:
            dir_fd = os.open(str(parent_path), dir_flags)
        except OSError as exc:
            return None, 0, None, ScanStatus.ERROR_UNREADABLE, _sanitize_error(exc)

        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            if hasattr(os, "openat"):
                file_fd = os.openat(dir_fd, name, flags)
            else:
                file_fd = os.open(str(parent_path / name), flags)
        except OSError as exc:
            err = _sanitize_error(exc)
            if getattr(exc, "errno", None) in (getattr(os, "ELOOP", -1), getattr(os, "EPERM", -1)):
                return None, 0, None, ScanStatus.ERROR_SYMLINK, err
            return None, 0, None, ScanStatus.ERROR_UNREADABLE, err

        try:
            st_before = os.fstat(file_fd)
        except OSError as exc:
            return None, 0, None, ScanStatus.ERROR_UNREADABLE, _sanitize_error(exc)

        if statmod.S_ISLNK(st_before.st_mode):
            return None, 0, None, ScanStatus.ERROR_SYMLINK, "entry is a symlink"
        if not statmod.S_ISREG(st_before.st_mode):
            return None, st_before.st_size, getattr(st_before, "st_mtime_ns", None), ScanStatus.ERROR_SPECIAL, "not a regular file"

        id_before = _stat_identity(st_before)
        try:
            sha, hashed_len = _hash_open_fd(file_fd, chunk_size=chunk_size)
        except OSError as exc:
            return None, st_before.st_size, getattr(st_before, "st_mtime_ns", None), ScanStatus.ERROR_HASH, _sanitize_error(exc)

        try:
            st_after = os.fstat(file_fd)
        except OSError as exc:
            return None, st_before.st_size, getattr(st_before, "st_mtime_ns", None), ScanStatus.ERROR_CHANGED, _sanitize_error(exc)

        if _stat_identity(st_after) != id_before or hashed_len != st_before.st_size:
            return None, st_before.st_size, getattr(st_before, "st_mtime_ns", None), ScanStatus.ERROR_CHANGED, "file changed during scan"

        try:
            if hasattr(os, "fstatat") and dir_fd is not None:
                st_dirent = os.fstatat(dir_fd, name, getattr(os, "AT_SYMLINK_NOFOLLOW", 0))
            else:
                st_dirent = os.lstat(str(parent_path / name))
            d_id = _stat_identity(st_dirent)
            if d_id[0] != id_before[0] or d_id[1] != id_before[1] or d_id[2] != id_before[2]:
                return None, st_before.st_size, getattr(st_before, "st_mtime_ns", None), ScanStatus.ERROR_CHANGED, "directory entry replaced during scan"
        except OSError as exc:
            return None, st_before.st_size, getattr(st_before, "st_mtime_ns", None), ScanStatus.ERROR_CHANGED, _sanitize_error(exc)

        return sha, st_before.st_size, getattr(st_before, "st_mtime_ns", None), ScanStatus.OK, None
    finally:
        if file_fd is not None:
            try:
                os.close(file_fd)
            except OSError:
                pass
        if dir_fd is not None:
            try:
                os.close(dir_fd)
            except OSError:
                pass


class _PublishReservation:
    """Stage all artifacts, fsync, exclusive no-clobber publish; roll back own outputs on failure."""

    def __init__(self, output_dir: Path, basenames: Sequence[str]) -> None:
        self.output_dir = output_dir
        self.basenames = list(basenames)
        self.stage_dir: Path | None = None
        self.published: list[Path] = []

    def __enter__(self) -> _PublishReservation:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for name in self.basenames:
            dest = self.output_dir / name
            if dest.exists():
                raise LegacyInventoryExistsError("output artifact already exists (no-clobber)", context={"path": str(dest)})
        self.stage_dir = Path(tempfile.mkdtemp(prefix=".leg001-stage-", dir=str(self.output_dir)))
        return self

    def stage_bytes(self, basename: str, data: bytes) -> None:
        assert self.stage_dir is not None
        dest = self.stage_dir / basename
        fd, tmp_name = tempfile.mkstemp(prefix=f".{basename}-", suffix=".partial", dir=str(self.stage_dir))
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.rename(str(tmp_path), str(dest))
            _fsync_file(dest)
        except Exception as exc:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise LegacyOutputError(f"failed to stage artifact: {exc}", context={"basename": basename}) from exc

    def publish(self) -> None:
        assert self.stage_dir is not None
        _fsync_dir(self.stage_dir)
        for name in self.basenames:
            staged = self.stage_dir / name
            if not staged.exists():
                raise LegacyOutputError("staged artifact missing before publication", context={"basename": name})
            final = self.output_dir / name
            if final.exists():
                self._rollback()
                raise LegacyInventoryExistsError("output artifact appeared during publication (no-clobber)", context={"path": str(final)})
            try:
                os.rename(str(staged), str(final))
            except (FileExistsError, OSError) as exc:
                self._rollback()
                if isinstance(exc, FileExistsError) or getattr(exc, "errno", None) in (getattr(os, "EEXIST", -1), getattr(os, "ENOTEMPTY", -1)):
                    raise LegacyInventoryExistsError("output artifact collision during publication", context={"path": str(final)}) from exc
                raise LegacyOutputError(f"atomic publication failed: {exc}", context={"path": str(final)}) from exc
            self.published.append(final)
            try:
                _fsync_file(final)
            except OSError as exc:
                self._rollback()
                raise LegacyOutputError(f"fsync after publish failed: {exc}", context={"path": str(final)}) from exc
        try:
            _fsync_dir(self.output_dir)
        except OSError:
            pass
        try:
            self.stage_dir.rmdir()
        except OSError:
            pass
        self.stage_dir = None

    def _rollback(self) -> None:
        for p in self.published:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        self.published.clear()

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type is not None:
            self._rollback()
        if self.stage_dir is not None and self.stage_dir.exists():
            for child in sorted(self.stage_dir.rglob("*"), reverse=True):
                try:
                    if child.is_file() or child.is_symlink():
                        child.unlink(missing_ok=True)
                    elif child.is_dir():
                        child.rmdir()
                except OSError:
                    pass
            try:
                self.stage_dir.rmdir()
            except OSError:
                pass
        return None


def _write_sorted_run(lines: list[tuple[str, str]], run_path: Path) -> None:
    lines.sort(key=lambda t: t[0])
    with run_path.open("w", encoding="utf-8") as handle:
        for _, line in lines:
            handle.write(line if line.endswith("\n") else line + "\n")


def _merge_runs(run_paths: list[Path], out_path: Path, *, fan_in: int = _MERGE_FAN_IN) -> None:
    if not run_paths:
        out_path.write_text("", encoding="utf-8")
        return
    if len(run_paths) == 1:
        out_path.write_bytes(run_paths[0].read_bytes())
        return
    if len(run_paths) > fan_in:
        intermediate: list[Path] = []
        parent = out_path.parent
        try:
            for i in range(0, len(run_paths), fan_in):
                batch = run_paths[i : i + fan_in]
                mid = parent / f".merge-mid-{i}.jsonl"
                _merge_runs(batch, mid, fan_in=fan_in)
                intermediate.append(mid)
            _merge_runs(intermediate, out_path, fan_in=fan_in)
        finally:
            for p in intermediate:
                p.unlink(missing_ok=True)
        return
    handles: list[io.TextIOWrapper] = []
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
        with out_path.open("w", encoding="utf-8") as out:
            while True:
                active = [h for h in heads if h is not None]
                if not active:
                    break
                active.sort(key=lambda t: t[0])
                _, best_line, best_idx = active[0]
                out.write(best_line if best_line.endswith("\n") else best_line + "\n")
                nxt = handles[best_idx].readline()
                if nxt:
                    obj = json.loads(nxt)
                    heads[best_idx] = (obj["relative_path"], nxt, best_idx)
                else:
                    heads[best_idx] = None
    finally:
        for h in handles:
            try:
                h.close()
            except OSError:
                pass


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
            raise LegacyConfigError("output_dir must not equal legacy_root", context={"root": root_resolved, "output_dir": out_resolved})

        out_rel_under_root: str | None = None
        try:
            rel = str(Path(out_resolved).relative_to(root_resolved)).replace("\\", "/")
            out_rel_under_root = "" if rel == "." else rel
        except ValueError:
            out_rel_under_root = None

        scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        basenames = [cfg.inventory_filename, cfg.summary_filename, cfg.duplicate_report_filename]

        work_dir = Path(tempfile.mkdtemp(prefix=".leg001-work-", dir=str(Path(out_resolved).parent)))
        path_db = work_dir / "paths.sqlite"
        hash_db = work_dir / "hashes.sqlite"
        runs_dir = work_dir / "runs"
        runs_dir.mkdir()
        queue_path = work_dir / "dir_queue.txt"

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
            line = json.dumps(entry.to_canonical_dict(), sort_keys=True, ensure_ascii=False, allow_nan=False)
            run_buffer.append((entry.relative_path, line))
            if len(run_buffer) >= _RUN_BUFFER_LIMIT:
                flush_run()
            counts_entry[entry.entry_type.value] = counts_entry.get(entry.entry_type.value, 0) + 1
            counts_evidence[entry.evidence_class.value] = counts_evidence.get(entry.evidence_class.value, 0) + 1
            counts_provenance[entry.provenance_class.value] = counts_provenance.get(entry.provenance_class.value, 0) + 1
            counts_status[entry.scan_status.value] = counts_status.get(entry.scan_status.value, 0) + 1
            total_entries += 1
            if entry.scan_status not in (ScanStatus.OK, ScanStatus.SKIPPED_EXCLUDED):
                error_count += 1

        def under_output(child_rel: str) -> bool:
            if out_rel_under_root is None or not out_rel_under_root:
                return False
            return child_rel == out_rel_under_root or child_rel.startswith(out_rel_under_root + "/")

        try:
            path_conn = sqlite3.connect(str(path_db))
            path_conn.execute("CREATE TABLE seen (rel TEXT PRIMARY KEY NOT NULL)")
            hash_conn = sqlite3.connect(str(hash_db))
            hash_conn.execute("CREATE TABLE hash_paths (sha256 TEXT NOT NULL, rel TEXT NOT NULL)")
            hash_conn.execute("CREATE INDEX idx_hp ON hash_paths(sha256)")

            with queue_path.open("w", encoding="utf-8") as qh:
                qh.write(str(root) + "\0" + "\n")

            queue_offset = 0
            while True:
                batch: list[tuple[str, str]] = []
                with queue_path.open("r", encoding="utf-8") as qh:
                    qh.seek(queue_offset)
                    for _ in range(_QUEUE_BATCH):
                        line = qh.readline()
                        if not line:
                            break
                        queue_offset = qh.tell()
                        line = line.rstrip("\n")
                        if "\0" not in line:
                            continue
                        abspath, rel = line.split("\0", 1)
                        batch.append((abspath, rel))
                if not batch:
                    break

                for abspath, rel in batch:
                    if out_rel_under_root is not None and (
                        rel == out_rel_under_root or (out_rel_under_root and rel.startswith(out_rel_under_root + "/"))
                    ):
                        excluded_by_rule["output_self"] = excluded_by_rule.get("output_self", 0) + 1
                        continue

                    try:
                        with os.scandir(abspath) as it:
                            for child in it:
                                child_name = child.name
                                try:
                                    child_name.encode("utf-8", errors="strict")
                                    unencodable = False
                                except UnicodeEncodeError:
                                    unencodable = True

                                child_rel = _join_rel(rel, child_name)
                                try:
                                    path_byte_len = len(child_rel.encode("utf-8", errors="replace"))
                                except Exception:
                                    path_byte_len = cfg.max_path_bytes + 1

                                if unencodable:
                                    emit(InventoryEntry(child_rel, EntryType.MALFORMED, None, None, None, EvidenceClass.UNKNOWN, ProvenanceClass.LEGACY_UNKNOWN, "unencodable_name", ScanStatus.ERROR_UNENCODABLE, "filename not strict UTF-8"))
                                    continue
                                if path_byte_len > cfg.max_path_bytes:
                                    emit(InventoryEntry(child_rel[:200] + "...", EntryType.MALFORMED, None, None, None, EvidenceClass.UNKNOWN, ProvenanceClass.LEGACY_UNKNOWN, "overlong_path", ScanStatus.ERROR_OVERLONG, f"path exceeds {cfg.max_path_bytes} bytes"))
                                    continue
                                try:
                                    path_conn.execute("INSERT INTO seen(rel) VALUES (?)", (child_rel,))
                                except sqlite3.IntegrityError:
                                    raise LegacyPathCollisionError("logical relative_path collision", context={"relative_path": child_rel}) from None

                                if under_output(child_rel):
                                    excluded_by_rule["output_self"] = excluded_by_rule.get("output_self", 0) + 1
                                    continue
                                if out_rel_under_root is not None and not out_rel_under_root:
                                    try:
                                        cr = str(Path(child.path).resolve())
                                        if cr == out_resolved or cr.startswith(out_resolved + os.sep):
                                            excluded_by_rule["output_self"] = excluded_by_rule.get("output_self", 0) + 1
                                            continue
                                    except OSError:
                                        pass

                                excl = _match_exclusion(child_rel, cfg.exclusion_rules)
                                if excl is not None:
                                    excluded_by_rule[excl] = excluded_by_rule.get(excl, 0) + 1
                                    is_dir = False
                                    try:
                                        is_dir = child.is_dir(follow_symlinks=False)
                                    except OSError:
                                        pass
                                    emit(InventoryEntry(child_rel, EntryType.DIRECTORY if is_dir else EntryType.REGULAR_FILE, None, None, None, EvidenceClass.UNKNOWN, ProvenanceClass.LEGACY_UNKNOWN, f"excluded:{excl}", ScanStatus.SKIPPED_EXCLUDED))
                                    continue

                                try:
                                    st = child.stat(follow_symlinks=False)
                                except OSError as exc:
                                    emit(InventoryEntry(child_rel, EntryType.UNREADABLE, None, None, None, EvidenceClass.UNKNOWN, ProvenanceClass.LEGACY_UNKNOWN, "lstat_error", ScanStatus.ERROR_UNREADABLE, _sanitize_error(exc)))
                                    continue

                                et = _entry_type_from_mode(st.st_mode)
                                if et is EntryType.DIRECTORY:
                                    with queue_path.open("a", encoding="utf-8") as qh:
                                        qh.write(child.path + "\0" + child_rel + "\n")
                                    ev, prov, basis = _classify(child_rel, cfg.classification_rules)
                                    emit(InventoryEntry(child_rel, et, None, getattr(st, "st_mtime_ns", None), None, ev, prov, basis, ScanStatus.OK))
                                    continue
                                if et is EntryType.SYMLINK:
                                    ev, prov, basis = _classify(child_rel, cfg.classification_rules)
                                    emit(InventoryEntry(child_rel, et, None, getattr(st, "st_mtime_ns", None), None, ev, prov, basis, ScanStatus.ERROR_SYMLINK, "symlink not followed"))
                                    continue
                                if et is EntryType.SPECIAL:
                                    ev, prov, basis = _classify(child_rel, cfg.classification_rules)
                                    emit(InventoryEntry(child_rel, et, st.st_size, getattr(st, "st_mtime_ns", None), None, ev, prov, basis, ScanStatus.ERROR_SPECIAL, "special file not hashed"))
                                    continue

                                sha, size, mtime_ns, status, err = _hash_regular_nofollow(Path(abspath), child_name, chunk_size=cfg.chunk_size)
                                if status is ScanStatus.OK and sha is not None:
                                    hashed_files += 1
                                    hashed_bytes += size
                                    hash_conn.execute("INSERT INTO hash_paths(sha256, rel) VALUES (?, ?)", (sha, child_rel))
                                ev, prov, basis = _classify(child_rel, cfg.classification_rules)
                                emit(InventoryEntry(child_rel, EntryType.REGULAR_FILE, size if size else None, mtime_ns, sha, ev, prov, basis, status, err))

                    except OSError as exc:
                        emit(InventoryEntry(rel or ".", EntryType.UNREADABLE, None, None, None, EvidenceClass.UNKNOWN, ProvenanceClass.LEGACY_UNKNOWN, "traversal_error", ScanStatus.ERROR_UNREADABLE, _sanitize_error(exc)))

            flush_run()
            path_conn.commit()
            hash_conn.commit()

            sorted_inv = work_dir / "sorted_inventory.jsonl"
            _merge_runs(run_paths, sorted_inv)
            inv_bytes = sorted_inv.read_bytes()
            inv_sha = hashlib.sha256(inv_bytes).hexdigest()

            dup_groups = 0
            dup_paths = 0
            dup_lines: list[tuple[str, str]] = []
            for sha, cnt in hash_conn.execute(
                "SELECT sha256, COUNT(*) AS c FROM hash_paths GROUP BY sha256 HAVING c > 1 ORDER BY sha256"
            ):
                paths = [row[0] for row in hash_conn.execute("SELECT rel FROM hash_paths WHERE sha256 = ? ORDER BY rel", (sha,))]
                dup_groups += 1
                dup_paths += len(paths)
                group = DuplicateGroup(sha256=sha, relative_paths=tuple(paths))
                line = json.dumps(group.to_canonical_dict(), sort_keys=True, ensure_ascii=False, allow_nan=False)
                dup_lines.append((sha, line))
            dup_body = "".join(ln + "\n" for _, ln in dup_lines)
            dup_bytes = dup_body.encode("utf-8")
            dup_sha = hashlib.sha256(dup_bytes).hexdigest()
            hash_conn.close()
            path_conn.close()

            summary = InventorySummary(
                root=str(root), root_resolved=root_resolved,
                scanner_version=SCANNER_VERSION, schema_version=INVENTORY_SCHEMA_VERSION,
                scanned_at_utc=scanned_at, total_entries=total_entries,
                hashed_regular_files=hashed_files, total_hashed_bytes=hashed_bytes,
                counts_by_entry_type=counts_entry, counts_by_evidence_class=counts_evidence,
                counts_by_provenance_class=counts_provenance, counts_by_scan_status=counts_status,
                excluded_by_rule=excluded_by_rule, duplicate_hash_groups=dup_groups,
                duplicate_path_count=dup_paths, error_count=error_count,
                inventory_sha256=inv_sha, inventory_byte_size=len(inv_bytes),
                inventory_uri=cfg.inventory_filename, summary_uri=cfg.summary_filename,
                duplicate_report_sha256=dup_sha, duplicate_report_byte_size=len(dup_bytes),
                duplicate_report_uri=cfg.duplicate_report_filename,
            )
            sum_bytes = _canonical_dumps(summary.to_canonical_dict()).encode("utf-8")

            with _PublishReservation(Path(out_resolved), basenames) as pub:
                pub.stage_bytes(cfg.inventory_filename, inv_bytes)
                pub.stage_bytes(cfg.duplicate_report_filename, dup_bytes)
                pub.stage_bytes(cfg.summary_filename, sum_bytes)
                pub.publish()
            return summary

        except LegacyScanError:
            raise
        except OSError as exc:
            raise LegacyOutputError(f"filesystem failure during scan: {exc}", context={"root": str(root)}) from exc
        finally:
            if work_dir.exists():
                for item in sorted(work_dir.rglob("*"), reverse=True):
                    try:
                        if item.is_file() or item.is_symlink():
                            item.unlink(missing_ok=True)
                        elif item.is_dir():
                            item.rmdir()
                    except OSError:
                        pass
                try:
                    work_dir.rmdir()
                except OSError:
                    pass


def scan_legacy_root(
    legacy_root: Path | str,
    output_dir: Path | str,
    *,
    config: ScanConfig | None = None,
) -> InventorySummary:
    """Scan a legacy root and write deterministic inventory artifacts."""
    return LegacyLocalScanner(config).scan(legacy_root, output_dir)
