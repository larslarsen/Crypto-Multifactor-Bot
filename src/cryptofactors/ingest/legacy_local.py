"""LEG-001 — Legacy local file scanner and deterministic inventory builder.

Forensic census only.  Registration does not imply acceptance.  Source bytes
are never rewritten, copied into the active store, or trusted as instrument
identity.  Classification is metadata, never promotion.
"""

from __future__ import annotations

import hashlib
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

# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

SCANNER_VERSION: Final[str] = "1.0.0"
INVENTORY_SCHEMA_VERSION: Final[str] = "1.0.0"

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LegacyScanError(Exception):
    """Base error for LEG-001 legacy scanner operations."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


class LegacyPathError(LegacyScanError):
    """Path safety, traversal, or root validation failure."""


class LegacyOutputError(LegacyScanError):
    """Inventory output publication or durability failure."""


class LegacyInventoryExistsError(LegacyOutputError):
    """Refuse to overwrite an existing inventory artifact."""


class LegacyTraversalError(LegacyScanError):
    """Filesystem traversal could not continue safely."""


# ---------------------------------------------------------------------------
# Enumerations (forensic metadata only — never acceptance)
# ---------------------------------------------------------------------------


class EntryType(str, Enum):
    REGULAR_FILE = "regular_file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    SPECIAL = "special"
    UNREADABLE = "unreadable"


class EvidenceClass(str, Enum):
    """Eight forensic classes from the legacy migration plan."""

    RAW_PROVIDER_OBJECT = "raw_provider_object"
    NORMALIZED_OBSERVATION = "normalized_observation"
    DERIVED_FEATURE = "derived_feature"
    LABEL_RETURN = "label_return"
    PREDICTION_MODEL_ARTIFACT = "prediction_model_artifact"
    REPORT_RESULT = "report_result"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class ProvenanceClass(str, Enum):
    """Provenance strength.  Heuristics may never assign VERIFIED_*."""

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


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClassificationRule:
    """Explicit, deterministic caller-supplied classification rule.

    ``match`` receives the normalized POSIX relative path and returns True when
    the rule applies.  Rules are evaluated in order; the first match wins.
    Provenance is never upgraded to VERIFIED_* by a rule — callers must set
    only LEGACY_* or leave the default.
    """

    name: str
    match: Callable[[str], bool]
    evidence_class: EvidenceClass
    provenance_class: ProvenanceClass = ProvenanceClass.LEGACY_UNKNOWN
    basis: str = ""


def _default_classification_rules() -> tuple[ClassificationRule, ...]:
    """Conservative path heuristics.  Never emit VERIFIED_* provenance."""

    def _re(pattern: str) -> Callable[[str], bool]:
        compiled = re.compile(pattern, re.IGNORECASE)

        def _m(rel: str) -> bool:
            return compiled.search(rel) is not None

        return _m

    return (
        ClassificationRule(
            name="config_dotfiles",
            match=_re(r"(^|/)\.(env|ini|cfg|conf|yaml|yml|toml|json)(\.|$)"),
            evidence_class=EvidenceClass.CONFIGURATION,
            basis="path pattern: config/dotfile",
        ),
        ClassificationRule(
            name="config_extensions",
            match=_re(r"\.(ya?ml|toml|ini|cfg|conf|json)$"),
            evidence_class=EvidenceClass.CONFIGURATION,
            basis="path pattern: config extension",
        ),
        ClassificationRule(
            name="model_artifacts",
            match=_re(
                r"\.(pkl|joblib|h5|hdf5|onnx|pt|pth|xgb|json)$|"
                r"(^|/)(models?|artifacts?|checkpoints?)/"
            ),
            evidence_class=EvidenceClass.PREDICTION_MODEL_ARTIFACT,
            basis="path pattern: model/artifact",
        ),
        ClassificationRule(
            name="reports_results",
            match=_re(
                r"(^|/)(reports?|results?|metrics?|evals?|figures?)/|"
                r"\.(png|jpg|jpeg|svg|pdf|html)$"
            ),
            evidence_class=EvidenceClass.REPORT_RESULT,
            basis="path pattern: report/result",
        ),
        ClassificationRule(
            name="labels_returns",
            match=_re(r"(^|/)(labels?|targets?|returns?)/"),
            evidence_class=EvidenceClass.LABEL_RETURN,
            basis="path pattern: label/return",
        ),
        ClassificationRule(
            name="features_derived",
            match=_re(r"(^|/)(features?|derived|indicators?)/"),
            evidence_class=EvidenceClass.DERIVED_FEATURE,
            basis="path pattern: derived/feature",
        ),
        ClassificationRule(
            name="normalized_bars",
            match=_re(
                r"(^|/)(canonical|normalized|bars?|ohlcv)/|"
                r"\.(parquet|pq)$"
            ),
            evidence_class=EvidenceClass.NORMALIZED_OBSERVATION,
            basis="path pattern: normalized/bar",
        ),
        ClassificationRule(
            name="raw_provider",
            match=_re(
                r"(^|/)(raw|provider|archive|downloads?|backfill)/|"
                r"\.(csv|zip|gz|bz2|zst)$"
            ),
            evidence_class=EvidenceClass.RAW_PROVIDER_OBJECT,
            basis="path pattern: raw/provider",
        ),
    )


# ---------------------------------------------------------------------------
# Exclusion
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExclusionRule:
    """Named exclusion.  ``match`` receives the normalized relative path."""

    name: str
    match: Callable[[str], bool]


def _default_exclusion_rules() -> tuple[ExclusionRule, ...]:
    def _seg(name: str) -> Callable[[str], bool]:
        def _m(rel: str) -> bool:
            parts = rel.split("/")
            return name in parts

        return _m

    def _suffixes(*suffixes: str) -> Callable[[str], bool]:
        lower = tuple(s.lower() for s in suffixes)

        def _m(rel: str) -> bool:
            base = rel.rsplit("/", 1)[-1].lower()
            return any(base.endswith(s) for s in lower)

        return _m

    def _names(*names: str) -> Callable[[str], bool]:
        s = {n.lower() for n in names}

        def _m(rel: str) -> bool:
            return rel.rsplit("/", 1)[-1].lower() in s

        return _m

    return (
        ExclusionRule(name="git_metadata", match=_seg(".git")),
        ExclusionRule(name="hg_metadata", match=_seg(".hg")),
        ExclusionRule(name="svn_metadata", match=_seg(".svn")),
        ExclusionRule(name="venv", match=_seg(".venv")),
        ExclusionRule(name="venv_dir", match=_seg("venv")),
        ExclusionRule(name="virtualenv", match=_seg(".virtualenv")),
        ExclusionRule(name="pycache", match=_seg("__pycache__")),
        ExclusionRule(name="mypy_cache", match=_seg(".mypy_cache")),
        ExclusionRule(name="pytest_cache", match=_seg(".pytest_cache")),
        ExclusionRule(name="ruff_cache", match=_seg(".ruff_cache")),
        ExclusionRule(name="ipynb_checkpoints", match=_seg(".ipynb_checkpoints")),
        ExclusionRule(name="node_modules", match=_seg("node_modules")),
        ExclusionRule(name="egg_info", match=lambda r: ".egg-info" in r.split("/")),
        ExclusionRule(name="dist", match=_seg("dist")),
        ExclusionRule(name="build", match=_seg("build")),
        ExclusionRule(name="tox", match=_seg(".tox")),
        ExclusionRule(name="nox", match=_seg(".nox")),
        ExclusionRule(name="idea", match=_seg(".idea")),
        ExclusionRule(name="vscode", match=_seg(".vscode")),
        ExclusionRule(name="ds_store", match=_names(".ds_store", "thumbs.db")),
        ExclusionRule(
            name="secret_files",
            match=_names(
                ".env",
                ".env.local",
                ".env.production",
                "secrets.yaml",
                "secrets.yml",
                "secrets.json",
                "credentials.json",
                "service_account.json",
            ),
        ),
        ExclusionRule(
            name="key_files",
            match=_suffixes(".key", ".pem", ".p12", ".pfx", ".jks", ".keystore"),
        ),
        ExclusionRule(
            name="python_bytecode",
            match=_suffixes(".pyc", ".pyo", ".pyd"),
        ),
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    """One discovered filesystem entry (forensic record)."""

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
class InventorySummary:
    """Deterministic scan summary."""

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
            "counts_by_evidence_class": dict(
                sorted(self.counts_by_evidence_class.items())
            ),
            "counts_by_provenance_class": dict(
                sorted(self.counts_by_provenance_class.items())
            ),
            "counts_by_scan_status": dict(sorted(self.counts_by_scan_status.items())),
            "excluded_by_rule": dict(sorted(self.excluded_by_rule.items())),
            "duplicate_hash_groups": self.duplicate_hash_groups,
            "duplicate_path_count": self.duplicate_path_count,
            "error_count": self.error_count,
            "inventory_sha256": self.inventory_sha256,
            "inventory_byte_size": self.inventory_byte_size,
            "inventory_uri": self.inventory_uri,
            "summary_uri": self.summary_uri,
        }


@dataclass(frozen=True, slots=True)
class ScanConfig:
    """Scanner configuration.  Defaults are secure and conservative."""

    chunk_size: int = 1024 * 1024
    classification_rules: Sequence[ClassificationRule] = field(
        default_factory=_default_classification_rules
    )
    exclusion_rules: Sequence[ExclusionRule] = field(
        default_factory=_default_exclusion_rules
    )
    follow_symlinks: bool = False  # always False for LEG-001
    inventory_filename: str = "legacy_inventory.jsonl"
    summary_filename: str = "legacy_inventory_summary.json"
    max_path_bytes: int = 4096

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise LegacyScanError(
                "chunk_size must be positive",
                context={"chunk_size": self.chunk_size},
            )
        if self.follow_symlinks:
            raise LegacyScanError(
                "follow_symlinks must be False for LEG-001 forensic scan",
            )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_rel(path: str) -> str:
    """Normalize to POSIX relative form without resolving symlinks."""
    text = path.replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    text = text.strip("/")
    if not text:
        return ""
    parts = [p for p in text.split("/") if p and p != "."]
    if any(p == ".." for p in parts):
        raise LegacyPathError(
            "relative path must not contain '..'",
            context={"path": path},
        )
    return "/".join(parts)


def _classify(
    rel: str,
    rules: Sequence[ClassificationRule],
) -> tuple[EvidenceClass, ProvenanceClass, str]:
    for rule in rules:
        if rule.match(rel):
            # Never allow heuristics to claim verified provenance.
            prov = rule.provenance_class
            if prov in (
                ProvenanceClass.VERIFIED_OFFICIAL,
                ProvenanceClass.VERIFIED_CROSSSOURCE,
            ):
                prov = ProvenanceClass.LEGACY_UNKNOWN
            return rule.evidence_class, prov, rule.basis or rule.name
    return EvidenceClass.UNKNOWN, ProvenanceClass.LEGACY_UNKNOWN, "default:unknown"


def _match_exclusion(
    rel: str,
    rules: Sequence[ExclusionRule],
) -> str | None:
    for rule in rules:
        if rule.match(rel):
            return rule.name
    return None


def _stream_sha256(path: Path, *, chunk_size: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def _sha256_of_file(path: Path, *, chunk_size: int = 1 << 20) -> str:
    """Streaming SHA-256 of an on-disk file (bounded memory)."""
    return _stream_sha256(path, chunk_size=chunk_size)[0]


def _canonical_dumps(obj: Any) -> str:
    return json.dumps(
        obj,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


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


def _atomic_publish_bytes(
    dest: Path,
    data: bytes | Path,
    *,
    label: str,
) -> None:
    """Write bytes via temp + fsync + exclusive link.  Never overwrites.

    ``data`` may be ``bytes`` (held in memory) or a ``pathlib.Path`` to a file
    that is streamed in chunks (so large inventories need not be buffered in
    RAM).  Race-safe: after the temp file is fsync'd, it is hard-linked onto
    ``dest`` with ``os.link``.  On POSIX ``os.link`` refuses to overwrite an
    existing destination (raises ``FileExistsError``), so a concurrent writer
    cannot clobber an existing inventory artifact.  Ordinary ``os.rename``
    would overwrite — that is why the link is used here.
    """
    if dest.exists():
        raise LegacyInventoryExistsError(
            f"{label} already exists (no-clobber)",
            context={"path": str(dest)},
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{label}-",
        suffix=".partial",
        dir=str(dest.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        _stream_buffer = 1 << 20  # 1 MiB
        with os.fdopen(fd, "wb") as handle:
            if isinstance(data, Path):
                with data.open("rb") as src:
                    while True:
                        chunk = src.read(_stream_buffer)
                        if not chunk:
                            break
                        handle.write(chunk)
            else:
                handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        # Fast-path: refuse if a writer created dest between our first check
        # and now.  The authoritative guarantee is the O_EXCL link below.
        if dest.exists():
            raise LegacyInventoryExistsError(
                f"{label} appeared during publish (no-clobber)",
                context={"path": str(dest)},
            )
        # Exclusive link: temp -> dest.  os.link does NOT overwrite an existing
        # destination; it raises FileExistsError instead.  Atomic on the same
        # filesystem (temp is created inside dest.parent by construction).
        try:
            os.link(str(tmp_path), str(dest))
        except FileExistsError:
            raise LegacyInventoryExistsError(
                f"{label} already exists (no-clobber, concurrent writer)",
                context={"path": str(dest)},
            ) from None
        _fsync_file(dest)
        _fsync_dir(dest.parent)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _entry_type_from_mode(mode: int) -> EntryType:
    if statmod.S_ISLNK(mode):
        return EntryType.SYMLINK
    if statmod.S_ISREG(mode):
        return EntryType.REGULAR_FILE
    if statmod.S_ISDIR(mode):
        return EntryType.DIRECTORY
    return EntryType.SPECIAL


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class LegacyLocalScanner:
    """Bounded-memory recursive scanner for a legacy local root.

    Public entry point: :meth:`scan`.
    """

    def __init__(self, config: ScanConfig | None = None) -> None:
        self._config = config or ScanConfig()

    def scan(
        self,
        legacy_root: Path | str,
        output_dir: Path | str,
    ) -> InventorySummary:
        """Inventory ``legacy_root`` and write deterministic artifacts to ``output_dir``.

        Parameters
        ----------
        legacy_root:
            Directory to census.  Must exist and be a real directory (not a
            symlink).  Source bytes are never modified.
        output_dir:
            Destination for ``legacy_inventory.jsonl`` and
            ``legacy_inventory_summary.json``.  Created if absent.  Existing
            inventory artifacts are refused (no-clobber).

        Returns
        -------
        InventorySummary
            Typed summary including inventory content hash.
        """
        root = Path(legacy_root)
        out = Path(output_dir)
        cfg = self._config

        try:
            root_st = os.lstat(root)
        except OSError as exc:
            raise LegacyPathError(
                f"cannot lstat legacy root: {exc}",
                context={"root": str(root)},
            ) from exc
        if statmod.S_ISLNK(root_st.st_mode):
            raise LegacyPathError(
                "legacy root must not be a symlink",
                context={"root": str(root)},
            )
        if not statmod.S_ISDIR(root_st.st_mode):
            raise LegacyPathError(
                "legacy root must be a directory",
                context={"root": str(root)},
            )

        root_resolved = str(Path(root).resolve())
        out.mkdir(parents=True, exist_ok=True)
        out_resolved = str(Path(out).resolve())

        inv_path = out / cfg.inventory_filename
        sum_path = out / cfg.summary_filename
        if inv_path.exists():
            raise LegacyInventoryExistsError(
                "inventory output already exists",
                context={"path": str(inv_path)},
            )
        if sum_path.exists():
            raise LegacyInventoryExistsError(
                "summary output already exists",
                context={"path": str(sum_path)},
            )

        # Self-exclusion: if output_dir is under legacy_root, skip that subtree.
        out_rel_under_root: str | None = None
        try:
            out_rel_under_root = _normalize_rel(
                str(Path(out_resolved).relative_to(root_resolved))
            )
        except ValueError:
            out_rel_under_root = None

        scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # On-disk spool for entries (bounded memory) + sqlite for duplicate index.
        spool_dir = Path(
            tempfile.mkdtemp(prefix=".leg001-spool-", dir=str(out))
        )
        spool_jsonl = spool_dir / "entries.jsonl"
        spool_db = spool_dir / "dup.sqlite"
        owned_temps: list[Path] = [spool_dir]

        counts_entry: dict[str, int] = {}
        counts_evidence: dict[str, int] = {}
        counts_provenance: dict[str, int] = {}
        counts_status: dict[str, int] = {}
        excluded_by_rule: dict[str, int] = {}
        total_entries = 0
        hashed_files = 0
        hashed_bytes = 0
        error_count = 0

        try:
            conn = sqlite3.connect(str(spool_db))
            conn.execute(
                "CREATE TABLE hash_paths (sha256 TEXT NOT NULL, rel TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE INDEX idx_hash ON hash_paths(sha256)"
            )

            with spool_jsonl.open("w", encoding="utf-8") as spool:
                # Iterative BFS — no recursion depth risk.
                # Stack holds (absolute_path, relative_posix).
                stack: list[tuple[Path, str]] = [(root, "")]
                while stack:
                    current, rel = stack.pop()
                    try:
                        with os.scandir(current) as it:
                            children = sorted(it, key=lambda e: e.name)
                    except OSError as exc:
                        entry = InventoryEntry(
                            relative_path=rel or ".",
                            entry_type=EntryType.UNREADABLE,
                            byte_size=None,
                            mtime_ns=None,
                            sha256=None,
                            evidence_class=EvidenceClass.UNKNOWN,
                            provenance_class=ProvenanceClass.LEGACY_UNKNOWN,
                            classification_basis="traversal_error",
                            scan_status=ScanStatus.ERROR_UNREADABLE,
                            error=str(exc),
                        )
                        self._emit(
                            spool,
                            entry,
                            counts_entry,
                            counts_evidence,
                            counts_provenance,
                            counts_status,
                        )
                        total_entries += 1
                        error_count += 1
                        continue

                    for child in children:
                        child_rel = (
                            f"{rel}/{child.name}" if rel else child.name
                        )
                        try:
                            child_rel = _normalize_rel(child_rel)
                        except LegacyPathError:
                            error_count += 1
                            continue

                        if len(child_rel.encode("utf-8", errors="replace")) > cfg.max_path_bytes:
                            error_count += 1
                            continue

                        # Self-exclusion of output area.
                        if out_rel_under_root is not None and (
                            child_rel == out_rel_under_root
                            or child_rel.startswith(out_rel_under_root + "/")
                        ):
                            excluded_by_rule["output_self"] = (
                                excluded_by_rule.get("output_self", 0) + 1
                            )
                            continue

                        excl = _match_exclusion(child_rel, cfg.exclusion_rules)
                        if excl is not None:
                            excluded_by_rule[excl] = excluded_by_rule.get(excl, 0) + 1
                            # Record the exclusion as an entry for auditability.
                            entry = InventoryEntry(
                                relative_path=child_rel,
                                entry_type=EntryType.DIRECTORY
                                if child.is_dir(follow_symlinks=False)
                                else EntryType.REGULAR_FILE,
                                byte_size=None,
                                mtime_ns=None,
                                sha256=None,
                                evidence_class=EvidenceClass.UNKNOWN,
                                provenance_class=ProvenanceClass.LEGACY_UNKNOWN,
                                classification_basis=f"excluded:{excl}",
                                scan_status=ScanStatus.SKIPPED_EXCLUDED,
                                error=None,
                            )
                            self._emit(
                                spool,
                                entry,
                                counts_entry,
                                counts_evidence,
                                counts_provenance,
                                counts_status,
                            )
                            total_entries += 1
                            # Do not descend into excluded directories.
                            continue

                        try:
                            st = child.stat(follow_symlinks=False)
                        except OSError as exc:
                            entry = InventoryEntry(
                                relative_path=child_rel,
                                entry_type=EntryType.UNREADABLE,
                                byte_size=None,
                                mtime_ns=None,
                                sha256=None,
                                evidence_class=EvidenceClass.UNKNOWN,
                                provenance_class=ProvenanceClass.LEGACY_UNKNOWN,
                                classification_basis="lstat_error",
                                scan_status=ScanStatus.ERROR_UNREADABLE,
                                error=str(exc),
                            )
                            self._emit(
                                spool,
                                entry,
                                counts_entry,
                                counts_evidence,
                                counts_provenance,
                                counts_status,
                            )
                            total_entries += 1
                            error_count += 1
                            continue

                        et = _entry_type_from_mode(st.st_mode)

                        if et is EntryType.DIRECTORY:
                            stack.append((Path(child.path), child_rel))
                            ev, prov, basis = _classify(
                                child_rel, cfg.classification_rules
                            )
                            entry = InventoryEntry(
                                relative_path=child_rel,
                                entry_type=et,
                                byte_size=None,
                                mtime_ns=getattr(st, "st_mtime_ns", None),
                                sha256=None,
                                evidence_class=ev,
                                provenance_class=prov,
                                classification_basis=basis,
                                scan_status=ScanStatus.OK,
                            )
                            self._emit(
                                spool,
                                entry,
                                counts_entry,
                                counts_evidence,
                                counts_provenance,
                                counts_status,
                            )
                            total_entries += 1
                            continue

                        if et is EntryType.SYMLINK:
                            ev, prov, basis = _classify(
                                child_rel, cfg.classification_rules
                            )
                            entry = InventoryEntry(
                                relative_path=child_rel,
                                entry_type=et,
                                byte_size=None,
                                mtime_ns=getattr(st, "st_mtime_ns", None),
                                sha256=None,
                                evidence_class=ev,
                                provenance_class=prov,
                                classification_basis=basis,
                                scan_status=ScanStatus.ERROR_SYMLINK,
                                error="symlink not followed",
                            )
                            self._emit(
                                spool,
                                entry,
                                counts_entry,
                                counts_evidence,
                                counts_provenance,
                                counts_status,
                            )
                            total_entries += 1
                            error_count += 1
                            continue

                        if et is EntryType.SPECIAL:
                            ev, prov, basis = _classify(
                                child_rel, cfg.classification_rules
                            )
                            entry = InventoryEntry(
                                relative_path=child_rel,
                                entry_type=et,
                                byte_size=st.st_size,
                                mtime_ns=getattr(st, "st_mtime_ns", None),
                                sha256=None,
                                evidence_class=ev,
                                provenance_class=prov,
                                classification_basis=basis,
                                scan_status=ScanStatus.ERROR_SPECIAL,
                                error="special file not hashed",
                            )
                            self._emit(
                                spool,
                                entry,
                                counts_entry,
                                counts_evidence,
                                counts_provenance,
                                counts_status,
                            )
                            total_entries += 1
                            error_count += 1
                            continue

                        # Regular file: stream hash + race check.
                        size_before = st.st_size
                        mtime_before = getattr(st, "st_mtime_ns", None)
                        sha: str | None = None
                        status = ScanStatus.OK
                        err: str | None = None
                        size_after = size_before
                        try:
                            sha, hashed_len = _stream_sha256(
                                Path(child.path), chunk_size=cfg.chunk_size
                            )
                            # Race detection: re-lstat and compare.
                            st2 = os.lstat(child.path)
                            size_after = st2.st_size
                            mtime_after = getattr(st2, "st_mtime_ns", None)
                            if (
                                size_after != size_before
                                or mtime_after != mtime_before
                                or hashed_len != size_before
                            ):
                                sha = None
                                status = ScanStatus.ERROR_CHANGED
                                err = "file changed during scan"
                                error_count += 1
                            else:
                                hashed_files += 1
                                hashed_bytes += size_after
                                conn.execute(
                                    "INSERT INTO hash_paths(sha256, rel) VALUES (?, ?)",
                                    (sha, child_rel),
                                )
                        except OSError as exc:
                            status = ScanStatus.ERROR_HASH
                            err = str(exc)
                            error_count += 1
                            sha = None

                        ev, prov, basis = _classify(
                            child_rel, cfg.classification_rules
                        )
                        entry = InventoryEntry(
                            relative_path=child_rel,
                            entry_type=EntryType.REGULAR_FILE,
                            byte_size=size_after if status is ScanStatus.OK else size_before,
                            mtime_ns=mtime_before,
                            sha256=sha,
                            evidence_class=ev,
                            provenance_class=prov,
                            classification_basis=basis,
                            scan_status=status,
                            error=err,
                        )
                        self._emit(
                            spool,
                            entry,
                            counts_entry,
                            counts_evidence,
                            counts_provenance,
                            counts_status,
                        )
                        total_entries += 1

            conn.commit()

            # Duplicate groups from on-disk index.
            dup_groups = 0
            dup_paths = 0
            for (cnt,) in conn.execute(
                "SELECT COUNT(*) FROM hash_paths GROUP BY sha256 HAVING COUNT(*) > 1"
            ):
                dup_groups += 1
                dup_paths += int(cnt)
            conn.close()

            # Build deterministic sorted inventory from spool WITHOUT loading
            # every record into memory.  External merge sort: each run holds at
            # most ``run_records`` (tuple[str, str]) entries, so peak memory is
            # O(run_records), independent of the total number of files scanned.
            run_records = 8192
            run_dir = Path(
                tempfile.mkdtemp(prefix=".leg001-runs-", dir=str(out))
            )
            run_paths: list[Path] = []
            owned_temps.append(run_dir)
            merged_path = run_dir / "merged_placeholder.jsonl"
            rel_key = lambda t: t[0]  # noqa: E731
            try:
                run: list[tuple[str, str]] = []
                with spool_jsonl.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.rstrip("\n")
                        if not line:
                            continue
                        obj = json.loads(line)
                        run.append((obj["relative_path"], line))
                        if len(run) >= run_records:
                            run.sort(key=rel_key)
                            rp = run_dir / f"run_{len(run_paths):04d}.jsonl"
                            rp.write_text(
                                "".join(r + "\n" for _, r in run),
                                encoding="utf-8",
                            )
                            run_paths.append(rp)
                            run = []
                if run:
                    run.sort(key=rel_key)
                    rp = run_dir / f"run_{len(run_paths):04d}.jsonl"
                    rp.write_text(
                        "".join(r + "\n" for _, r in run),
                        encoding="utf-8",
                    )
                    run_paths.append(rp)

                # K-way merge of the sorted runs INTO a temp output file,
                # streaming line-by-line so peak memory stays bounded.
                import heapq

                merged_path = run_dir / f"merged_{len(run_paths):04d}.jsonl"
                with merged_path.open("w", encoding="utf-8") as out_fh:
                    streams = [rp.open("r", encoding="utf-8") for rp in run_paths]
                    try:
                        heap: list[tuple[str, int, str]] = []
                        for i, s in enumerate(streams):
                            first = s.readline()
                            if first:
                                obj = json.loads(first)
                                heapq.heappush(heap, (obj["relative_path"], i, first))
                        while heap:
                            _, i, line = heapq.heappop(heap)
                            out_fh.write(line if line.endswith("\n") else line + "\n")
                            nxt = streams[i].readline()
                            if nxt:
                                obj = json.loads(nxt)
                                heapq.heappush(heap, (obj["relative_path"], i, nxt))
                    finally:
                        for s in streams:
                            s.close()

                # Hash + publish the merged file by streaming (no full in-RAM
                # buffer), then drop the run dir.  Do this inside the outer try
                # block so the merged file is still present.
                inv_sha = _sha256_of_file(merged_path)
                _atomic_publish_bytes(inv_path, merged_path, label="inventory")
            finally:
                for rp in run_paths:
                    rp.unlink(missing_ok=True)
                merged_path.unlink(missing_ok=True)
                if run_dir.exists():
                    run_dir.rmdir()

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
                inventory_byte_size=inv_path.stat().st_size,
                inventory_uri=cfg.inventory_filename,
                summary_uri=cfg.summary_filename,
            )
            sum_bytes = _canonical_dumps(summary.to_canonical_dict()).encode("utf-8")
            _atomic_publish_bytes(sum_path, sum_bytes, label="summary")
            return summary

        except Exception:
            # Clean only temps we own.
            for p in owned_temps:
                if p.is_dir():
                    for item in sorted(p.rglob("*"), reverse=True):
                        try:
                            if item.is_file() or item.is_symlink():
                                item.unlink(missing_ok=True)
                            elif item.is_dir():
                                item.rmdir()
                        except OSError:
                            pass
                    try:
                        p.rmdir()
                    except OSError:
                        pass
            raise
        finally:
            # Success path: remove spool after outputs published.
            if spool_dir.exists():
                for item in sorted(spool_dir.rglob("*"), reverse=True):
                    try:
                        if item.is_file() or item.is_symlink():
                            item.unlink(missing_ok=True)
                        elif item.is_dir():
                            item.rmdir()
                    except OSError:
                        pass
                try:
                    spool_dir.rmdir()
                except OSError:
                    pass

    @staticmethod
    def _emit(
        spool: Any,
        entry: InventoryEntry,
        counts_entry: dict[str, int],
        counts_evidence: dict[str, int],
        counts_provenance: dict[str, int],
        counts_status: dict[str, int],
    ) -> None:
        d = entry.to_canonical_dict()
        # Compact single-line JSON, sorted keys for determinism within the line.
        spool.write(
            json.dumps(d, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
        )
        counts_entry[entry.entry_type.value] = (
            counts_entry.get(entry.entry_type.value, 0) + 1
        )
        counts_evidence[entry.evidence_class.value] = (
            counts_evidence.get(entry.evidence_class.value, 0) + 1
        )
        counts_provenance[entry.provenance_class.value] = (
            counts_provenance.get(entry.provenance_class.value, 0) + 1
        )
        counts_status[entry.scan_status.value] = (
            counts_status.get(entry.scan_status.value, 0) + 1
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def scan_legacy_root(
    legacy_root: Path | str,
    output_dir: Path | str,
    *,
    config: ScanConfig | None = None,
) -> InventorySummary:
    """Scan a legacy root and write deterministic inventory artifacts.

    See :class:`LegacyLocalScanner` for full semantics.
    """
    return LegacyLocalScanner(config).scan(legacy_root, output_dir)
