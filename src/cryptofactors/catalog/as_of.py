"""ASOF-001 — reviewed as-of access for catalog datasets.

Implements the architecture ``AsOfStore`` contract
(``docs/architecture/03_DOMAIN_INTERFACES.md`` §6) with strict temporal
eligibility (``docs/architecture/01_DATA_ARCHITECTURE.md`` §12).

Layer: catalog only (may import ``core``). Market-bar rows are read from published
MAN-001 dataset trees; REF-001 / FEE-001 tables are read from the control SQLite
database without importing the ``reference`` package.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.errors import UnsafePathError
from cryptofactors.catalog.dataset.paths import lexical_join

# ---------------------------------------------------------------------------
# Public constants — logical dataset ids for control-catalog reference tables
# ---------------------------------------------------------------------------

LOGICAL_REF_INSTRUMENT_VERSION = "ref_instrument_version"
LOGICAL_REF_FEE_SCHEDULE = "ref_fee_schedule"
MARKET_BARS_DATASET_TYPE = "market_bars"

_US_PER_SECOND = 1_000_000


class AsOfAccessError(RuntimeError):
    """Raised when as-of access inputs or dataset bindings are invalid."""

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


def _require_utc(dt: datetime, *, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise AsOfAccessError(f"{field} must be a datetime", context={"type": type(dt).__name__})
    if dt.tzinfo is None:
        raise AsOfAccessError(f"{field} must be timezone-aware UTC", context={"value": str(dt)})
    return dt.astimezone(timezone.utc)


def _dt_to_us(dt: datetime) -> int:
    u = _require_utc(dt, field="timestamp")
    return int(u.timestamp() * _US_PER_SECOND)


def _parse_iso_to_us(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise AsOfAccessError("stored timestamp must be timezone-aware", context={"value": value})
    return _dt_to_us(dt.astimezone(timezone.utc))


# ---------------------------------------------------------------------------
# Eligibility (architecture §12)
# ---------------------------------------------------------------------------


def observation_eligible(
    *,
    decision_time_us: int,
    availability_time_us: int | None,
    valid_from_us: int | None = None,
    valid_to_us: int | None = None,
) -> bool:
    """Observation row eligibility at decision time ``t`` (UTC µs).

    Requires ``availability_time <= t``. When valid bounds are supplied:
    ``valid_from <= t <= valid_to`` (closed upper bound when ``valid_to`` is None).
    """
    if availability_time_us is None:
        return False
    if availability_time_us > decision_time_us:
        return False
    if valid_from_us is not None and valid_from_us > decision_time_us:
        return False
    if valid_to_us is not None and decision_time_us > valid_to_us:
        return False
    return True


def reference_eligible(
    *,
    decision_time_us: int,
    knowledge_time_us: int,
    valid_from_us: int | None,
    valid_to_us: int | None,
    known_from_us: int | None,
    known_to_us: int | None,
    availability_time_us: int | None = None,
) -> bool:
    """Reference-fact eligibility at decision time ``t`` and knowledge time ``k``.

    ``valid_from <= t < valid_to`` and ``known_from <= k < known_to`` (open ends
    allowed). When ``availability_time`` is present it must also be ``<= t``.
    """
    if valid_from_us is None or known_from_us is None:
        return False
    if valid_from_us > decision_time_us:
        return False
    if valid_to_us is not None and decision_time_us >= valid_to_us:
        return False
    if known_from_us > knowledge_time_us:
        return False
    if known_to_us is not None and knowledge_time_us >= known_to_us:
        return False
    if availability_time_us is not None and availability_time_us > decision_time_us:
        return False
    return True


@runtime_checkable
class AsOfStore(Protocol):
    """Architecture as-of observation interface (extended with ``as_of``)."""

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> pa.Table: ...

    def as_of(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        knowledge_time: datetime | None = None,
    ) -> pa.Table: ...


@dataclass(frozen=True, slots=True)
class CatalogAsOfStore:
    """Concrete as-of store over MAN-001 datasets and control-catalog reference tables.

    Parameters
    ----------
    control_database:
        SQLite control catalog (datasets + REF/FEE tables after migrations).
    dataset_store_root:
        Filesystem root for published MAN-001 dataset trees (required for market bars).
    """

    control_database: Path
    dataset_store_root: Path | None = None

    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None = None,
    ) -> pa.Table:
        """Return the latest eligible row per key at ``decision_time``.

        Enforces ``availability_time <= decision_time`` (and reference known/valid
        windows with knowledge time equal to decision time). When ``max_age`` is
        set, rows whose availability is older than ``decision_time - max_age`` are
        excluded.
        """
        t = _require_utc(decision_time, field="decision_time")
        t_us = _dt_to_us(t)
        min_availability_us: int | None = None
        if max_age is not None:
            if max_age.total_seconds() < 0:
                raise AsOfAccessError("max_age must be non-negative")
            min_availability_us = t_us - int(max_age.total_seconds() * _US_PER_SECOND)

        kind = self._resolve_kind(dataset_id)
        if kind == "market_bars":
            table = self._load_market_bars(dataset_id, keys, fields)
            return self._latest_market_bars(table, keys, fields, t_us, min_availability_us)
        if kind == "ref_fee_schedule":
            return self._latest_fee_schedules(keys, fields, t_us, t_us, min_availability_us)
        if kind == "ref_instrument_version":
            return self._latest_instrument_versions(
                keys, fields, t_us, t_us, min_availability_us
            )
        raise AsOfAccessError(
            "unsupported dataset for latest_available",
            context={"dataset_id": dataset_id, "kind": kind},
        )

    def as_of(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time: datetime,
        knowledge_time: datetime | None = None,
    ) -> pa.Table:
        """Return all rows eligible at ``decision_time`` / ``knowledge_time``.

        When ``knowledge_time`` is omitted it defaults to ``decision_time``.
        No silent fallbacks: missing keys yield no rows.
        """
        t = _require_utc(decision_time, field="decision_time")
        k = _require_utc(knowledge_time, field="knowledge_time") if knowledge_time else t
        t_us = _dt_to_us(t)
        k_us = _dt_to_us(k)

        kind = self._resolve_kind(dataset_id)
        if kind == "market_bars":
            table = self._load_market_bars(dataset_id, keys, fields)
            return self._filter_market_bars(table, keys, fields, t_us)
        if kind == "ref_fee_schedule":
            return self._filter_fee_schedules(keys, fields, t_us, k_us)
        if kind == "ref_instrument_version":
            return self._filter_instrument_versions(keys, fields, t_us, k_us)
        raise AsOfAccessError(
            "unsupported dataset for as_of",
            context={"dataset_id": dataset_id, "kind": kind},
        )

    # ------------------------------------------------------------------
    # Dataset binding
    # ------------------------------------------------------------------

    def _resolve_kind(self, dataset_id: str) -> str:
        text = dataset_id.strip()
        if not text:
            raise AsOfAccessError("dataset_id must be non-empty")
        if text in {
            LOGICAL_REF_FEE_SCHEDULE,
            "venue_fee_schedule",
            "FEE-001",
        }:
            return "ref_fee_schedule"
        if text in {
            LOGICAL_REF_INSTRUMENT_VERSION,
            "reference_instruments",
            "REF-001",
        }:
            return "ref_instrument_version"
        # MAN-001 published dataset
        cat = SqliteDatasetCatalog(self.control_database)
        try:
            row = cat.get_dataset(text)
        finally:
            cat.close()
        if row is None:
            raise AsOfAccessError(
                "dataset_id not found in catalog",
                context={"dataset_id": text},
            )
        dtype = str(row.get("dataset_type") or "")
        if dtype == MARKET_BARS_DATASET_TYPE or text.startswith("ds_"):
            if dtype and dtype != MARKET_BARS_DATASET_TYPE:
                raise AsOfAccessError(
                    "dataset_type is not market_bars",
                    context={"dataset_id": text, "dataset_type": dtype},
                )
            return "market_bars"
        raise AsOfAccessError(
            "unsupported catalog dataset_type for as-of access",
            context={"dataset_id": text, "dataset_type": dtype},
        )

    def _dataset_file_paths(self, dataset_id: str) -> list[Path]:
        if self.dataset_store_root is None:
            raise AsOfAccessError(
                "dataset_store_root is required for market_bars as-of access",
                context={"dataset_id": dataset_id},
            )
        cat = SqliteDatasetCatalog(self.control_database)
        try:
            files = list(cat.list_files(dataset_id))
            ds_row = cat.get_dataset(dataset_id)
        finally:
            cat.close()
        if not files:
            raise AsOfAccessError(
                "dataset has no registered files",
                context={"dataset_id": dataset_id},
            )
        root = Path(self.dataset_store_root).expanduser()
        if not root.is_absolute():
            root = Path.cwd() / root

        # Resolve the dataset's base directory from manifest_uri if available.
        # MAN-001 publishes files under store_root/datasets/sha256/<prefix>/<id>/<relative_path>,
        # and storage_uri is the relative_path within that dataset directory.
        # The manifest_uri (e.g. "datasets/sha256/<prefix>/<id>/manifest.json") tells us
        # the dataset directory relative to store_root.
        dataset_base = root
        if ds_row is not None:
            manifest_uri = str(ds_row.get("manifest_uri") or "")
            if manifest_uri:
                dataset_dir = str(Path(manifest_uri).parent)
                try:
                    dataset_base = lexical_join(root, dataset_dir)
                except UnsafePathError as exc:
                    raise AsOfAccessError(
                        f"unsafe dataset manifest path: {exc}",
                        context={"manifest_uri": manifest_uri},
                    ) from exc

        paths: list[Path] = []
        for f in files:
            uri = str(f.get("storage_uri") or "")
            if not uri:
                continue
            try:
                paths.append(lexical_join(dataset_base, uri))
            except UnsafePathError as exc:
                raise AsOfAccessError(
                    f"unsafe dataset file path: {exc}",
                    context={"storage_uri": uri},
                ) from exc
        if not paths:
            raise AsOfAccessError(
                "dataset files missing storage_uri",
                context={"dataset_id": dataset_id},
            )
        return paths

    def _load_market_bars(
        self,
        dataset_id: str,
        keys: Sequence[int | str],
        fields: Sequence[str],
    ) -> pa.Table:
        paths = self._dataset_file_paths(dataset_id)
        tables: list[pa.Table] = []
        for path in paths:
            if not path.exists():
                raise AsOfAccessError(
                    "dataset parquet missing on disk",
                    context={"path": str(path)},
                )
            tables.append(pq.read_table(path))
        if not tables:
            return self._empty_table(fields)
        table = pa.concat_tables(tables, promote_options="default")
        return table

    # ------------------------------------------------------------------
    # Market bars (BAR-001)
    # ------------------------------------------------------------------

    def _filter_market_bars(
        self,
        table: pa.Table,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time_us: int,
    ) -> pa.Table:
        if table.num_rows == 0:
            return self._project(table, fields)
        required = ("instrument_id", "period_start", "period_end", "availability_time")
        for col in required:
            if col not in table.column_names:
                raise AsOfAccessError(
                    f"market_bars table missing column {col!r}",
                    context={"columns": list(table.column_names)},
                )
        key_set = {int(k) for k in keys}
        if not key_set:
            return self._project(table.slice(0, 0), fields)

        # Build boolean mask row-wise for eligibility (clear, fail-closed).
        inst = table.column("instrument_id").to_pylist()
        p_start = table.column("period_start").to_pylist()
        p_end = table.column("period_end").to_pylist()
        avail = table.column("availability_time").to_pylist()
        keep: list[bool] = []
        for i in range(table.num_rows):
            iid = inst[i]
            if iid is None or int(iid) not in key_set:
                keep.append(False)
                continue
            a = avail[i]
            vf = p_start[i]
            vt = p_end[i]
            if a is None or vf is None:
                keep.append(False)
                continue
            keep.append(
                observation_eligible(
                    decision_time_us=decision_time_us,
                    availability_time_us=int(a),
                    valid_from_us=int(vf),
                    valid_to_us=int(vt) if vt is not None else None,
                )
            )
        mask = pa.array(keep, type=pa.bool_())
        filtered = table.filter(mask)
        return self._project(filtered, fields)

    def _latest_market_bars(
        self,
        table: pa.Table,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time_us: int,
        min_availability_us: int | None,
    ) -> pa.Table:
        """Latest completed bar per key at ``decision_time``.

        Completed-bar access uses availability only (plus optional ``period_start``
        lower bound): ``availability_time <= t`` and ``period_start <= t``. The
        period upper bound is intentionally not applied — a bar remains selectable
        after ``period_end`` once it has become available (production BAR-001 sets
        ``availability_time = period_end``).
        """
        if table.num_rows == 0:
            return self._project(table, fields)
        required = ("instrument_id", "period_start", "period_end", "availability_time")
        for col in required:
            if col not in table.column_names:
                raise AsOfAccessError(
                    f"market_bars table missing column {col!r}",
                    context={"columns": list(table.column_names)},
                )
        key_set = {int(k) for k in keys}
        if not key_set:
            return self._project(table.slice(0, 0), fields)

        inst = table.column("instrument_id").to_pylist()
        p_start = table.column("period_start").to_pylist()
        avail = table.column("availability_time").to_pylist()
        keep: list[bool] = []
        for i in range(table.num_rows):
            iid = inst[i]
            if iid is None or int(iid) not in key_set:
                keep.append(False)
                continue
            a = avail[i]
            vf = p_start[i]
            if a is None or vf is None:
                keep.append(False)
                continue
            a_us = int(a)
            vf_us = int(vf)
            if a_us > decision_time_us:
                keep.append(False)
                continue
            if vf_us > decision_time_us:
                keep.append(False)
                continue
            if min_availability_us is not None and a_us < min_availability_us:
                keep.append(False)
                continue
            keep.append(True)
        mask = pa.array(keep, type=pa.bool_())
        eligible = table.filter(mask)
        if eligible.num_rows == 0:
            return self._project(eligible, fields)

        # Per instrument_id keep row with max (period_start, availability_time).
        inst = eligible.column("instrument_id").to_pylist()
        p_start = eligible.column("period_start").to_pylist()
        avail = eligible.column("availability_time").to_pylist()
        best: dict[int, int] = {}
        best_key: dict[int, tuple[int, int]] = {}
        for i in range(eligible.num_rows):
            iid = int(inst[i])
            rank = (int(p_start[i]), int(avail[i]))
            if iid not in best or rank > best_key[iid]:
                best[iid] = i
                best_key[iid] = rank
        indices = pa.array(sorted(best.values()), type=pa.int64())
        latest = eligible.take(indices)
        return self._project(latest, fields)

    # ------------------------------------------------------------------
    # Fee schedules (FEE-001) via control SQLite
    # ------------------------------------------------------------------

    def _connect_control(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.control_database))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _filter_fee_schedules(
        self,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time_us: int,
        knowledge_time_us: int,
        *,
        min_availability_us: int | None = None,
    ) -> pa.Table:
        key_set = {str(k) for k in keys}
        if not key_set and keys is not None:
            # Empty key list means no instruments requested → empty result.
            return self._empty_fee_table(fields)
        conn = self._connect_control()
        try:
            rows = conn.execute(
                "SELECT * FROM ref_fee_schedule ORDER BY instrument_id, fee_tier_id, fee_schedule_id"
            ).fetchall()
        except sqlite3.Error as exc:
            raise AsOfAccessError(
                f"cannot read ref_fee_schedule: {exc}",
                context={"database": str(self.control_database)},
            ) from exc
        finally:
            conn.close()

        out: list[dict[str, Any]] = []
        for r in rows:
            iid = str(r["instrument_id"])
            if iid not in key_set:
                continue
            vf = _parse_iso_to_us(r["valid_from"])
            vt = _parse_iso_to_us(r["valid_to"])
            kf = _parse_iso_to_us(r["known_from"])
            kt = _parse_iso_to_us(r["known_to"])
            # Reference availability: known_from is when the system may consume it.
            if not reference_eligible(
                decision_time_us=decision_time_us,
                knowledge_time_us=knowledge_time_us,
                valid_from_us=vf,
                valid_to_us=vt,
                known_from_us=kf,
                known_to_us=kt,
                availability_time_us=kf,
            ):
                continue
            if min_availability_us is not None and kf is not None and kf < min_availability_us:
                continue
            out.append(self._fee_row_dict(r, vf, vt, kf, kt))
        return self._fee_dicts_to_table(out, fields)

    def _latest_fee_schedules(
        self,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time_us: int,
        knowledge_time_us: int,
        min_availability_us: int | None,
    ) -> pa.Table:
        # Load full eligible rows then reduce per (instrument_id, fee_tier_id).
        table = self._filter_fee_schedules(
            keys,
            fields=(),  # empty → all columns
            decision_time_us=decision_time_us,
            knowledge_time_us=knowledge_time_us,
            min_availability_us=min_availability_us,
        )
        if table.num_rows == 0:
            return self._project(table, fields) if fields else table
        rows = table.to_pylist()
        best: dict[tuple[str, str], tuple[tuple[Any, ...], dict[str, Any]]] = {}
        for row in rows:
            key = (str(row["instrument_id"]), str(row["fee_tier_id"]))
            rank = (
                int(row["valid_from_us"]),
                int(row["known_from_us"]),
                str(row["fee_schedule_id"]),
            )
            prev = best.get(key)
            if prev is None or rank > prev[0]:
                best[key] = (rank, row)
        selected = [item[1] for item in best.values()]
        return self._fee_dicts_to_table(selected, fields)

    def _fee_row_dict(
        self,
        r: sqlite3.Row,
        vf: int | None,
        vt: int | None,
        kf: int | None,
        kt: int | None,
    ) -> dict[str, Any]:
        return {
            "fee_schedule_id": r["fee_schedule_id"],
            "instrument_id": r["instrument_id"],
            "fee_tier_id": r["fee_tier_id"],
            "maker_fee_rate": r["maker_fee_rate"],
            "taker_fee_rate": r["taker_fee_rate"],
            "evidence_class": r["evidence_class"],
            "valid_from": r["valid_from"],
            "valid_to": r["valid_to"],
            "known_from": r["known_from"],
            "known_to": r["known_to"],
            "valid_from_us": vf,
            "valid_to_us": vt,
            "known_from_us": kf,
            "known_to_us": kt,
            "availability_time_us": kf,
            "supersedes_fee_schedule_id": r["supersedes_fee_schedule_id"],
            "evidence_json": r["evidence_json"],
        }

    def _fee_dicts_to_table(
        self, rows: list[dict[str, Any]], fields: Sequence[str]
    ) -> pa.Table:
        if not rows:
            return self._empty_fee_table(fields)
        table = pa.Table.from_pylist(rows)
        if not fields:
            return table
        return self._project(table, fields)

    def _empty_fee_table(self, fields: Sequence[str]) -> pa.Table:
        schema_map = {
            "fee_schedule_id": pa.string(),
            "instrument_id": pa.string(),
            "fee_tier_id": pa.string(),
            "maker_fee_rate": pa.string(),
            "taker_fee_rate": pa.string(),
            "evidence_class": pa.string(),
            "valid_from": pa.string(),
            "valid_to": pa.string(),
            "known_from": pa.string(),
            "known_to": pa.string(),
            "valid_from_us": pa.int64(),
            "valid_to_us": pa.int64(),
            "known_from_us": pa.int64(),
            "known_to_us": pa.int64(),
            "availability_time_us": pa.int64(),
            "supersedes_fee_schedule_id": pa.string(),
            "evidence_json": pa.string(),
        }
        cols = list(fields) if fields else list(schema_map)
        arrays = []
        names = []
        for c in cols:
            if c not in schema_map:
                continue
            names.append(c)
            arrays.append(pa.array([], type=schema_map[c]))
        if not names:
            names = ["instrument_id"]
            arrays = [pa.array([], type=pa.string())]
        return pa.Table.from_arrays(arrays, names=names)

    # ------------------------------------------------------------------
    # Instrument versions (REF-001)
    # ------------------------------------------------------------------

    def _filter_instrument_versions(
        self,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time_us: int,
        knowledge_time_us: int,
        *,
        min_availability_us: int | None = None,
    ) -> pa.Table:
        key_set = {str(k) for k in keys}
        if not key_set:
            return self._empty_instr_ver_table(fields)
        conn = self._connect_control()
        try:
            rows = conn.execute(
                "SELECT * FROM ref_instrument_version "
                "ORDER BY instrument_id, version_seq, instrument_version_id"
            ).fetchall()
        except sqlite3.Error as exc:
            raise AsOfAccessError(
                f"cannot read ref_instrument_version: {exc}",
                context={"database": str(self.control_database)},
            ) from exc
        finally:
            conn.close()

        out: list[dict[str, Any]] = []
        for r in rows:
            iid = str(r["instrument_id"])
            if iid not in key_set:
                continue
            vf = _parse_iso_to_us(r["valid_from"])
            vt = _parse_iso_to_us(r["valid_to"])
            kf = _parse_iso_to_us(r["known_from"])
            kt = _parse_iso_to_us(r["known_to"])
            if not reference_eligible(
                decision_time_us=decision_time_us,
                knowledge_time_us=knowledge_time_us,
                valid_from_us=vf,
                valid_to_us=vt,
                known_from_us=kf,
                known_to_us=kt,
                availability_time_us=kf,
            ):
                continue
            if min_availability_us is not None and kf is not None and kf < min_availability_us:
                continue
            out.append(
                {
                    "instrument_version_id": r["instrument_version_id"],
                    "instrument_id": r["instrument_id"],
                    "version_seq": int(r["version_seq"]),
                    "contract_spec_json": r["contract_spec_json"],
                    "valid_from": r["valid_from"],
                    "valid_to": r["valid_to"],
                    "known_from": r["known_from"],
                    "known_to": r["known_to"],
                    "valid_from_us": vf,
                    "valid_to_us": vt,
                    "known_from_us": kf,
                    "known_to_us": kt,
                    "availability_time_us": kf,
                    "supersedes_version_id": r["supersedes_version_id"],
                    "evidence_json": r["evidence_json"],
                }
            )
        if not out:
            return self._empty_instr_ver_table(fields)
        table = pa.Table.from_pylist(out)
        if not fields:
            return table
        return self._project(table, fields)

    def _latest_instrument_versions(
        self,
        keys: Sequence[int | str],
        fields: Sequence[str],
        decision_time_us: int,
        knowledge_time_us: int,
        min_availability_us: int | None,
    ) -> pa.Table:
        table = self._filter_instrument_versions(
            keys,
            fields=(),
            decision_time_us=decision_time_us,
            knowledge_time_us=knowledge_time_us,
            min_availability_us=min_availability_us,
        )
        if table.num_rows == 0:
            return self._project(table, fields) if fields else table
        rows = table.to_pylist()
        best: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {}
        for row in rows:
            iid = str(row["instrument_id"])
            rank = (
                int(row["version_seq"]),
                int(row["valid_from_us"]),
                int(row["known_from_us"]),
                str(row["instrument_version_id"]),
            )
            prev = best.get(iid)
            if prev is None or rank > prev[0]:
                best[iid] = (rank, row)
        selected = [item[1] for item in best.values()]
        if not selected:
            return self._empty_instr_ver_table(fields)
        out = pa.Table.from_pylist(selected)
        if not fields:
            return out
        return self._project(out, fields)

    def _empty_instr_ver_table(self, fields: Sequence[str]) -> pa.Table:
        schema_map = {
            "instrument_version_id": pa.string(),
            "instrument_id": pa.string(),
            "version_seq": pa.int64(),
            "contract_spec_json": pa.string(),
            "valid_from": pa.string(),
            "valid_to": pa.string(),
            "known_from": pa.string(),
            "known_to": pa.string(),
            "valid_from_us": pa.int64(),
            "valid_to_us": pa.int64(),
            "known_from_us": pa.int64(),
            "known_to_us": pa.int64(),
            "availability_time_us": pa.int64(),
            "supersedes_version_id": pa.string(),
            "evidence_json": pa.string(),
        }
        cols = list(fields) if fields else list(schema_map)
        names: list[str] = []
        arrays: list[pa.Array] = []
        for c in cols:
            if c not in schema_map:
                continue
            names.append(c)
            arrays.append(pa.array([], type=schema_map[c]))
        if not names:
            names = ["instrument_id"]
            arrays = [pa.array([], type=pa.string())]
        return pa.Table.from_arrays(arrays, names=names)

    # ------------------------------------------------------------------
    # Projection helpers
    # ------------------------------------------------------------------

    def _project(self, table: pa.Table, fields: Sequence[str]) -> pa.Table:
        if not fields:
            return table
        missing = [f for f in fields if f not in table.column_names]
        if missing:
            raise AsOfAccessError(
                "requested fields not present in result",
                context={"missing": missing, "available": list(table.column_names)},
            )
        return table.select(list(fields))

    def _empty_table(self, fields: Sequence[str]) -> pa.Table:
        if not fields:
            return pa.table({"_empty": pa.array([], type=pa.null())})
        arrays = [pa.array([], type=pa.null()) for _ in fields]
        return pa.Table.from_arrays(arrays, names=list(fields))
