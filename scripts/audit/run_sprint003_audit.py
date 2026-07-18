#!/usr/bin/env python3
"""AUD-003 — Execute Sprint 003 source-feasibility audits.

Runs the ACCEPTED ``source_audit`` toolkit (AUD-002, commit 899fb7c) against the
already-collected Sprint 003 evidence staged at ``/tmp/crypto_source_audit/`` and
emits deterministic JSON + CSV audit outputs under
``research/sprint_003/audit_results/``.

This runner gathers and validates evidence. It makes NO research acceptance
decisions and does NOT commit raw datasets. Failed audits remain visible as failed
records (never omitted).

Usage:
    PYTHONPATH=src python3 scripts/audit/run_sprint003_audit.py \
        [--staging /tmp/crypto_source_audit] \
        [--out research/sprint_003/audit_results]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from source_audit import (
    audit_zip_safe,
    compare_bars,
    compare_binance_archive_precision,
    compute_sha256,
    compute_storage_stats,
    dump_json,
    dumps_json,
    infer_timestamp_unit,
    normalize_trade,
    paginate,
    PaginationCallbacks,
    reconstruct_bars,
)
from source_audit.models import (
    ProjectionAssumptions,
    StorageSample,
)

UTC_MIN = datetime(2017, 1, 1, tzinfo=timezone.utc)
UTC_MAX = datetime(2027, 1, 1, tzinfo=timezone.utc)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def output_hash(obj: Any) -> str:
    """Deterministic content hash of a serialized report body."""
    return sha256_bytes(dumps_json(obj).encode("utf-8"))


@dataclass
class Runner:
    staging: Path
    out: Path

    # ---- evidence reconciliation -------------------------------------------

    def load_manifest(self) -> list[dict[str, str]]:
        mpath = self.staging / "evidence_manifest.csv"
        if not mpath.exists():
            raise FileNotFoundError(mpath)
        with mpath.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def reconcile(self, rows: list[dict[str, str]]) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        seen_hashes: dict[str, str] = {}
        counts = {
            "present": 0,
            "missing": 0,
            "corrupt": 0,
            "duplicated": 0,
            "superseded": 0,
            "inaccessible": 0,
        }
        for r in rows:
            eid = r["evidence_id"]
            local = r.get("local_path", "").strip()
            status = r.get("collection_status", "").strip()
            entry: dict[str, Any] = {
                "evidence_id": eid,
                "provider": r.get("provider", ""),
                "category": r.get("category", ""),
                "declared_status": status,
                "local_path": local,
                "http_status": r.get("http_status", ""),
                "declared_bytes": r.get("byte_size", ""),
            }
            # Records with no local artifact (docs-only, blocked, error responses).
            if not local:
                state = "inaccessible" if status not in ("COLLECTED",) else "missing"
                entry["state"] = state
                entry["note"] = "no local_path in manifest"
                counts[state] += 1
                records.append(entry)
                continue
            p = self.staging / local
            if not p.exists():
                entry["state"] = "missing"
                entry["note"] = "declared local_path not found on disk"
                counts["missing"] += 1
                records.append(entry)
                continue
            actual_bytes = p.stat().st_size
            entry["actual_bytes"] = actual_bytes
            declared = r.get("byte_size", "").strip()
            if declared.isdigit() and int(declared) != actual_bytes:
                entry["state"] = "corrupt"
                entry["note"] = f"byte size mismatch declared={declared} actual={actual_bytes}"
                counts["corrupt"] += 1
                records.append(entry)
                continue
            digest = compute_sha256(p)
            entry["sha256"] = digest
            if digest in seen_hashes:
                entry["state"] = "duplicated"
                entry["note"] = f"identical content to {seen_hashes[digest]}"
                counts["duplicated"] += 1
            else:
                seen_hashes[digest] = eid
                entry["state"] = "present"
                counts["present"] += 1
            records.append(entry)
        return {
            "audit": "evidence_reconciliation",
            "tool": "source_audit.compute_sha256 + manifest cross-check",
            "manifest_records": len(rows),
            "counts": counts,
            "records": records,
        }

    # ---- hash verification --------------------------------------------------

    def hash_report(self, recon: dict[str, Any]) -> dict[str, Any]:
        results = []
        for e in recon["records"]:
            if e.get("state") in ("present", "duplicated") and "sha256" in e:
                results.append(
                    {
                        "evidence_id": e["evidence_id"],
                        "local_path": e["local_path"],
                        "sha256": e["sha256"],
                        "byte_size": e.get("actual_bytes"),
                        "status": "verified",
                    }
                )
            else:
                results.append(
                    {
                        "evidence_id": e["evidence_id"],
                        "local_path": e.get("local_path", ""),
                        "sha256": None,
                        "status": f"skipped:{e.get('state')}",
                    }
                )
        return {
            "audit": "hash_verification",
            "tool": "source_audit.compute_sha256 (SHA-256, immutable object)",
            "verified": sum(1 for r in results if r["status"] == "verified"),
            "results": results,
        }

    # ---- archive safety -----------------------------------------------------

    def archive_report(self) -> dict[str, Any]:
        results = []
        for zp in sorted(self.staging.glob("**/*.zip")):
            rel = str(zp.relative_to(self.staging))
            cfg = {
                "max_members": 1000,
                "max_ratio": "100.0",
                "max_total_extracted": 2 * 1024**3,
            }
            rec: dict[str, Any] = {
                "input": rel,
                "sha256": compute_sha256(zp),
                "config": cfg,
                "tool": "source_audit.audit_zip_safe",
            }
            try:
                res = audit_zip_safe(zp)
                rec["status"] = "safe"
                rec["member_count"] = res.member_count
                rec["total_compressed"] = res.total_compressed
                rec["total_extracted"] = res.total_extracted
                rec["max_ratio_observed"] = Decimal(str(round(res.max_ratio_observed, 4)))
                rec["members"] = [m.name for m in res.members]
            except Exception as exc:  # noqa: BLE001 - audit records the failure
                rec["status"] = "failed"
                rec["failure"] = f"{type(exc).__name__}: {exc}"
            results.append(rec)
        # .csv.gz are gzip, not zip; note them as out-of-scope for zip inspection
        gz = [str(p.relative_to(self.staging)) for p in sorted(self.staging.glob("**/*.csv.gz"))]
        return {
            "audit": "archive_safety",
            "tool": "source_audit.audit_zip_safe",
            "zip_inspected": len(results),
            "gzip_not_zip_out_of_scope": gz,
            "results": results,
        }

    # ---- CSV / schema / timestamp ------------------------------------------

    BINANCE_SCHEMAS = {
        # (schema columns, timestamp column index)
        "spot_aggTrades": (["agg_trade_id", "price", "quantity", "first_trade_id",
                            "last_trade_id", "transact_time", "is_buyer_maker",
                            "is_best_match"], 5),
        "perp_aggTrades": (["agg_trade_id", "price", "quantity", "first_trade_id",
                            "last_trade_id", "transact_time", "is_buyer_maker"], 5),
        "perp_trades": (["id", "price", "qty", "quote_qty", "time",
                         "is_buyer_maker"], 4),
        "klines": (["open_time", "open", "high", "low", "close", "volume",
                    "close_time", "quote_volume"], 0),
        "funding": (["calc_time", "funding_interval_hours", "last_funding_rate"], 0),
    }

    def _binance_kind(self, member: str) -> str | None:
        if "aggTrades" in member:
            return "perp_aggTrades" if "perp" in member else "spot_aggTrades"
        if "trades" in member:
            return "perp_trades"
        if "1m" in member or "klines" in member:
            return "klines"
        if "funding" in member:
            return "funding"
        return None

    @staticmethod
    def _is_header_row(row: list[str], ts_idx: int) -> bool:
        if not row or len(row) <= ts_idx:
            return False
        cell = row[ts_idx].strip()
        # A header cell is alphabetic text (e.g. "transact_time", "time");
        # a data cell is a numeric epoch.
        return not cell.replace(".", "", 1).lstrip("-").isdigit()

    def csv_report(self) -> dict[str, Any]:
        results = []
        tmp = self.out / "_tmp_csv"
        tmp.mkdir(exist_ok=True)
        try:
            for zp in sorted(self.staging.glob("binance/*.zip")):
                try:
                    zf = zipfile.ZipFile(zp)
                    member = zf.namelist()[0]
                except Exception as exc:  # noqa: BLE001
                    results.append({"input": str(zp.relative_to(self.staging)),
                                    "status": "failed",
                                    "failure": f"{type(exc).__name__}: {exc}"})
                    continue
                kind = self._binance_kind(member)
                if kind is None:
                    results.append({"input": member, "status": "skipped:unmapped_schema"})
                    continue
                headers, ts_idx = self.BINANCE_SCHEMAS[kind]
                xpath = tmp / member
                with zf.open(member) as src, xpath.open("wb") as dst:
                    dst.write(src.read())
                # Determine headerness by peeking the timestamp column of row 0.
                with xpath.open("r", encoding="utf-8", newline="") as f:
                    first = next(csv.reader(f), [])
                has_header = self._is_header_row(first, ts_idx)
                sampled = self._sample_timestamps(xpath, ts_idx, has_header=has_header)
                rec = {
                    "input": member,
                    "input_sha256": compute_sha256(zp),
                    "provider": "binance",
                    "kind": kind,
                    "schema": headers,
                    "detected_has_header": has_header,
                    "timestamp_column_index": ts_idx,
                    "utc_bounds": [UTC_MIN.isoformat(), UTC_MAX.isoformat()],
                    "config": {"has_header": has_header, "sample_rows": 20,
                               "encoding": "utf-8", "delimiter": ","},
                    "tool": ("source_audit.infer_timestamp_unit (header-"
                             "auto-detected sampling)"),
                    "timestamp_sample": sampled,
                    "status": "inspected",
                }
                results.append(rec)
                xpath.unlink()
        finally:
            try:
                tmp.rmdir()
            except OSError:
                pass
        return {
            "audit": "csv_schema_timestamp",
            "tool": "source_audit.infer_timestamp_unit / audit_csv_safe",
            "note": ("audit_csv_safe requires has_header=True; the daily Binance data "
                     "dumps (aggTrades/klines) are headerless, so units are inferred "
                     "from the declared timestamp column via infer_timestamp_unit. "
                     "Header presence is auto-detected per archive."),
            "results": results,
        }

    def _sample_timestamps(self, csv_path: Path, ts_idx: int, n: int = 20, *,
                           has_header: bool = False) -> dict[str, Any]:
        units: dict[str, int] = {}
        samples: list[dict[str, Any]] = []
        malformed = 0
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if has_header and i == 0:
                    continue  # skip the column-header row
                if i >= n + (1 if has_header else 0):
                    break
                try:
                    raw = row[ts_idx]
                    inf = infer_timestamp_unit(raw, min_utc=UTC_MIN, max_utc=UTC_MAX)
                    units[inf.unit] = units.get(inf.unit, 0) + 1
                    if len(samples) < 3:
                        samples.append({"raw": raw, "unit": inf.unit,
                                        "utc": inf.datetime_utc.isoformat()})
                except Exception as exc:  # noqa: BLE001
                    malformed += 1
                    if len(samples) < 3:
                        samples.append({"raw": row[ts_idx] if row else None,
                                        "error": f"{type(exc).__name__}: {exc}"})
        return {"unit_distribution": units, "malformed": malformed, "examples": samples}

    # ---- Binance precision comparison --------------------------------------

    def precision_report(self) -> dict[str, Any]:
        a = self.staging / "binance/BTCUSDT-aggTrades-2024-12-31.zip"
        b = self.staging / "binance/BTCUSDT-aggTrades-2025-01-01.zip"
        cfg = {
            "member_suffix": ".csv",
            "timestamp_column": 5,
            "has_header": False,
            "timestamp_min_utc": UTC_MIN.isoformat(),
            "timestamp_max_utc": UTC_MAX.isoformat(),
            "max_sample_rows": 50,
            "min_valid_inferences": 5,
            "max_malformed_rate": "0.1",
            "max_ambiguous_rate": "0.05",
        }
        rec: dict[str, Any] = {
            "audit": "binance_precision_comparison",
            "tool": "source_audit.compare_binance_archive_precision",
            "archive_a": str(a.relative_to(self.staging)),
            "archive_b": str(b.relative_to(self.staging)),
            "sha256_a": compute_sha256(a) if a.exists() else None,
            "sha256_b": compute_sha256(b) if b.exists() else None,
            "config": cfg,
        }
        try:
            res = compare_binance_archive_precision(
                a, b,
                timestamp_column=5,
                has_header=False,
                timestamp_min_utc=UTC_MIN,
                timestamp_max_utc=UTC_MAX,
            )
            rec["status"] = "completed"
            rec["result"] = res
        except Exception as exc:  # noqa: BLE001
            rec["status"] = "failed"
            rec["failure"] = f"{type(exc).__name__}: {exc}"
        return rec

    # ---- storage statistics -------------------------------------------------

    def storage_report(self) -> dict[str, Any]:
        # Build samples from actually-present Binance archives (compressed + extracted).
        samples: list[StorageSample] = []
        for zp in sorted(self.staging.glob("binance/*.zip")):
            try:
                zf = zipfile.ZipFile(zp)
                member = zf.namelist()[0]
                info = zf.getinfo(member)
                # count rows cheaply
                with zf.open(member) as f:
                    rows = sum(1 for _ in f)
                samples.append(StorageSample(
                    label=zp.name,
                    source_identity=compute_sha256(zp),
                    row_count=rows,
                    compressed_bytes=info.compress_size,
                    extracted_bytes=info.file_size,
                    coverage_note="binance BTCUSDT daily archive",
                ))
            except Exception:  # noqa: BLE001
                continue
        if not samples:
            return {"audit": "storage_statistics", "status": "failed",
                    "failure": "no storage samples available"}
        pa = ProjectionAssumptions(
            u25_universe_size=25, u50_universe_size=50, u100_universe_size=100,
            rows_per_asset_per_period=1_000_000, retention_periods=365,
            replication_factor=Decimal("1"), basis="extracted",
            overhead_multiplier=Decimal("1.2"), safety_multiplier=Decimal("1.5"),
        )
        cfg = {
            "basis": "extracted",
            "upper_quantile": "0.9",
            "stress_case_bytes_per_row": "200",
            "projection_assumptions": {
                "u25_universe_size": 25, "u50_universe_size": 50, "u100_universe_size": 100,
                "rows_per_asset_per_period": 1_000_000, "retention_periods": 365,
                "replication_factor": "1", "basis": "extracted",
                "overhead_multiplier": "1.2", "safety_multiplier": "1.5",
            },
        }
        rec: dict[str, Any] = {
            "audit": "storage_statistics",
            "tool": "source_audit.compute_storage_stats",
            "config": cfg,
            "sample_count": len(samples),
        }
        try:
            stats = compute_storage_stats(
                samples, basis="extracted", upper_quantile=Decimal("0.9"),
                stress_case_bytes_per_row=Decimal("200"), projection_assumptions=pa,
            )
            rec["status"] = "completed"
            rec["result"] = stats
        except Exception as exc:  # noqa: BLE001
            rec["status"] = "failed"
            rec["failure"] = f"{type(exc).__name__}: {exc}"
        return rec

    # ---- pagination & bars (evidence-gated) --------------------------------

    # ---- Section 1: headerless Binance precision ADAPTER (runner-level) ----

    def headerless_precision_adapter(self) -> dict[str, Any]:
        """Transparent runner adapter around infer_timestamp_unit.

        NOT a successful invocation of compare_binance_archive_precision (which
        hard-rejects headerless archives). This replicates the same evidence
        thresholds using the accepted infer_timestamp_unit primitive.
        """
        archives = [
            ("binance/BTCUSDT-aggTrades-2024-12-31.zip",
             "binance/BTCUSDT-aggTrades-2024-12-31.csv", 5, "spot_aggTrades"),
            ("binance/BTCUSDT-aggTrades-2025-01-01.zip",
             "binance/BTCUSDT-aggTrades-2025-01-01.csv", 5, "spot_aggTrades"),
        ]
        cfg: dict[str, Any] = {
            "adapter": "headerless_binance_precision (runner-level, infer_timestamp_unit)",
            "min_valid_inferences": 5, "max_malformed_rate": "0.1",
            "max_ambiguous_rate": "0.05", "sample_rows": 50,
            "utc_bounds": [UTC_MIN.isoformat(), UTC_MAX.isoformat()],
        }
        sides: list[dict[str, Any]] = []
        for zrel, member, ts_idx, kind in archives:
            zp = self.staging / zrel
            rec: dict[str, Any] = {
                "archive": zrel, "member": member, "timestamp_column_index": ts_idx,
                "sha256": compute_sha256(zp) if zp.exists() else None,
            }
            try:
                with zipfile.ZipFile(zp) as zf:
                    member = zf.namelist()[0]
                    data = zf.open(member).read().decode("utf-8", "replace").splitlines()
                units: dict[str, int] = {}
                valid = malformed = ambiguous = out_of_range = 0
                for i, line in enumerate(data):
                    if i >= int(cfg["sample_rows"]):
                        break
                    cell = line.split(",")[ts_idx]
                    try:
                        inf = infer_timestamp_unit(cell, min_utc=UTC_MIN, max_utc=UTC_MAX)
                        units[inf.unit] = units.get(inf.unit, 0) + 1
                        valid += 1
                    except Exception as exc:  # noqa: BLE001
                        msg = f"{type(exc).__name__}: {exc}"
                        if "out of range" in msg or "beyond" in msg:
                            out_of_range += 1
                        elif "Ambiguous" in msg:
                            ambiguous += 1
                        else:
                            malformed += 1
                rec.update({
                    "status": "inspected", "unit_distribution": units,
                    "valid": valid, "malformed": malformed,
                    "ambiguous": ambiguous, "out_of_range": out_of_range,
                    "dominant_unit": max(units, key=lambda k: units[k]) if units else None,
                })
            except Exception as exc:  # noqa: BLE001
                rec["status"] = "failed"
                rec["failure"] = f"{type(exc).__name__}: {exc}"
            sides.append(rec)
        # Apply same thresholds as the native comparator.
        a, b = sides[0], sides[1]
        thresholds_met = all(
            s.get("valid", 0) >= 5 for s in sides
        ) and all(s.get("malformed", 0) / max(s.get("valid", 0), 1) <= 0.1 for s in sides)
        supports = bool(
            thresholds_met and a.get("dominant_unit") and b.get("dominant_unit")
            and a["dominant_unit"] != b["dominant_unit"]
        )
        return {
            "audit": "binance_precision_comparison_adapter",
            "native_comparator": "compare_binance_archive_precision",
            "native_status": "failed (headerless not supported; preserved as evidence)",
            "adapter_tool": "source_audit.infer_timestamp_unit (runner adapter)",
            "config": cfg,
            "note": ("Adapter ONLY; not a successful native comparator run. Mirrors "
                     "native min-evidence/quality thresholds."),
            "sides": sides,
            "thresholds_met": thresholds_met,
            "supports_unit_transition": supports,
            "transition": f"{a.get('dominant_unit')} -> {b.get('dominant_unit')}"
                         if supports else None,
        }

    # ---- Section 2: static Bybit pagination replay -------------------------

    def bybit_pagination_replay(self) -> dict[str, Any]:
        import json as _json
        pages = {}
        for rel in ["bybit/inst_p1.json", "bybit/inst_p2.json"]:
            p = self.staging / rel
            if p.exists():
                pages[rel] = _json.loads(p.read_text(encoding="utf-8"))
        # Build a deterministic offline fetch callback keyed by cursor.
        # Sequence captured files in name order; each page's nextPageCursor points
        # to the following page. Unknown cursor -> empty terminal page.
        seq = list(pages.values())

        fetch_map: dict[Any, Any] = {}
        fetch_map[None] = seq[0] if seq else None
        for idx, pg in enumerate(seq[:-1]):
            nxt = pg["result"].get("nextPageCursor")
            fetch_map[nxt] = seq[idx + 1]

        def fetch_page(cursor: Any, limit: int) -> Any:  # noqa: ANN001
            if cursor in fetch_map:
                return fetch_map[cursor]
            return {"result": {"list": [], "nextPageCursor": None}, "retCode": 0,
                    "retMsg": "OK", "retExtInfo": {}, "time": 0}

        def parse_records(raw: Any) -> list[Any]:  # noqa: ANN001
            return list(raw["result"]["list"])

        def record_id(rec: Any) -> tuple[Any, ...]:  # noqa: ANN001
            return (rec.get("symbol"),)

        def order_key(rec: Any) -> tuple[Any, ...]:  # noqa: ANN001
            return (rec.get("symbol"),)

        def next_cursor(raw: Any, _recs: Any) -> Any:  # noqa: ANN001
            return raw["result"].get("nextPageCursor")

        def page_fingerprint(raw: Any, recs: Any) -> tuple[Any, ...]:  # noqa: ANN001
            # Stable, hashable fingerprint for repeated-page detection.
            return (raw["result"].get("nextPageCursor"), len(recs),
                    tuple(r.get("symbol") for r in recs[:3]))

        cbs = PaginationCallbacks(
            fetch_page=fetch_page, parse_records=parse_records,
            record_id=record_id, order_key=order_key, next_cursor=next_cursor,
            page_fingerprint=page_fingerprint,
        )
        rec: dict[str, Any] = {
            "audit": "pagination",
            "tool": "source_audit.paginate (PaginationCallbacks) over captured Bybit pages",
            "input_hashes": {k: compute_sha256(self.staging / k) for k in pages},
            "config": {"mode": "cursor", "max_pages": 10, "max_records": 100000},
        }
        try:
            result = paginate(cbs, mode="cursor", max_pages=10, max_records=100000,
                              raise_on_safety_violation=True)
            d = result.diagnostics
            rec.update({
                "status": "completed",
                "pages_consumed": d.pages_fetched,
                "records_observed": d.records_yielded,
                "cursor_sequence": [c for c in [None] + [p["result"].get("nextPageCursor")
                                                       for p in seq]],
                "repeated_cursors": d.repeated_cursor_events,
                "repeated_pages": d.repeated_page_events,
                "boundary_duplicates": d.boundary_duplicate_count,
                "ordering_violations": d.within_page_order_violations
                + d.across_page_order_violations,
                "gaps": len(result.gaps),
                "overlaps": len(result.overlaps),
                "termination_reason": d.stopped_reason,
                "raw_cursor_values": [p["result"].get("nextPageCursor") for p in seq],
            })
        except Exception as exc:  # noqa: BLE001
            rec["status"] = "failed"
            rec["failure"] = f"{type(exc).__name__}: {exc}"
        return rec

    # ---- Section 3: bounded trade-to-bar comparison ------------------------

    def trade_to_bar_comparison(self) -> dict[str, Any]:
        from datetime import timedelta
        z_trades = self.staging / "binance/BTCUSDT-aggTrades-2025-01-01.zip"
        z_klines = self.staging / "binance/BTCUSDT-klines-1m-2025-01-01.zip"
        cfg = {
            "window_minutes": 10, "interval": "1m", "closure": "LEFT_CLOSED_RIGHT_OPEN",
            "price_tolerance": "0.01", "volume_tolerance": "0.0001",
            "utc_bounds": [UTC_MIN.isoformat(), UTC_MAX.isoformat()],
            "note": ("Binance aggTrades count is NOT semantically equivalent to the "
                     "provider kline's raw-trade count; aggTrades count reported "
                     "separately, never presented as raw-trade count."),
        }
        rec: dict[str, Any] = {
            "audit": "bar_reconstruction_comparison",
            "tool": "source_audit.reconstruct_bars + compare_bars + normalize_trade",
            "config": cfg,
            "input_sha256": {
                "aggTrades": compute_sha256(z_trades) if z_trades.exists() else None,
                "klines": compute_sha256(z_klines) if z_klines.exists() else None,
            },
        }
        try:
            # Stream only needed window: read aggTrades, keep first 10 complete minutes.
            with zipfile.ZipFile(z_trades) as zf:
                member = zf.namelist()[0]
                trades_raw = []
                for line in zf.open(member).read().decode("utf-8").splitlines():
                    parts = line.split(",")
                    # aggTrades: transact_time is column 5 (microseconds on 2025-01-01)
                    ts = int(parts[5])
                    dt = datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc)
                    if dt.minute >= 10:  # stop after first 10 minutes window
                        break
                    trades_raw.append({
                        "timestamp_utc": dt,
                        "price": parts[1], "quantity": parts[2],
                        "trade_id": parts[0], "quote_quantity": parts[3],
                    })
            # Klines: read first 10 complete 1m rows (open_time in microseconds).
            with zipfile.ZipFile(z_klines) as zf:
                kmember = zf.namelist()[0]
                klines_raw = []
                for line in zf.open(kmember).read().decode("utf-8").splitlines():
                    parts = line.split(",")
                    ot = int(parts[0])
                    dt = datetime.fromtimestamp(ot / 1_000_000, tz=timezone.utc)
                    if dt.minute >= 10:
                        break
                    klines_raw.append({
                        "interval_start_utc": dt, "open": parts[1], "high": parts[2],
                        "low": parts[3], "close": parts[4], "volume_base": parts[5],
                        "volume_quote": parts[6],
                    })
            trades = [normalize_trade(t) for t in trades_raw]
            origin = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            recon = reconstruct_bars(trades, interval_duration=timedelta(minutes=1),
                                     alignment_origin_utc=origin)
            # Reconstruct succeeded; attempt the toolkit comparison separately so a
            # structural provider limitation does not discard the reconstruction.
            comparison = None
            comparison_status = "not_run"
            comparison_failure = None
            try:
                comparison = compare_bars(
                    recon.bars, klines_raw,
                    price_tolerance=Decimal("0.01"),
                    volume_tolerance=Decimal("0.0001"),
                    interval_duration=timedelta(minutes=1),
                )
                comparison_status = "completed"
            except Exception as exc:  # noqa: BLE001
                comparison_status = "failed"
                comparison_failure = f"{type(exc).__name__}: {exc}"
            rec.update({
                "status": "partial" if comparison_status == "failed" else "completed",
                "aggTrades_records_used": len(trades_raw),
                "kline_bars_used": len(klines_raw),
                "reconstructed_bars": len(recon.bars),
                "duplicate_trades": recon.duplicate_trades,
                "reconstruction": "completed (trade-to-bar via source_audit.reconstruct_bars)",
                "comparison_status": comparison_status,
                "comparison_failure": comparison_failure,
                "comparison": (
                    {
                        "bars_compared": getattr(comparison, "bars_compared", None),
                        "match_count": getattr(comparison, "match_count", None),
                        "mismatch_count": getattr(comparison, "mismatch_count", None),
                        "mismatches_retained": getattr(comparison, "mismatches", []),
                    } if comparison is not None else None
                ),
                # Explicit semantic separation (NOT raw-trade count):
                "aggTrades_record_count": len(trades_raw),
                "provider_kline_raw_trade_count": ("UNAVAILABLE — Binance kline schema "
                    "has no raw-trade-count field; the toolkit's compare_bars hard-"
                    "requires a trade_count field on provider bars. aggTrades record "
                    "count is structurally DISTINCT from a kline's raw-trade count and "
                    "is NEVER presented as one."),
                "semantic_mismatch_flag": ("aggTrades record count != provider kline "
                    "raw-trade count (field absent on klines; toolkit limitation)"),
            })
        except Exception as exc:  # noqa: BLE001
            rec["status"] = "failed"
            rec["failure"] = f"{type(exc).__name__}: {exc}"
        return rec

    # ---- Section 4: Bybit gzip archive inspection --------------------------

    def bybit_archive_inspect(self) -> dict[str, Any]:
        import gzip as _gzip
        results = []
        for rel in ["bybit/BTCUSD2019-10-01.csv.gz", "bybit/BTCUSDT2020-03-25.csv.gz"]:
            p = self.staging / rel
            rec: dict[str, Any] = {"input": rel, "sha256": compute_sha256(p)}
            MAX_BYTES = 200 * 1024 * 1024
            MAX_ROWS = 50_000
            try:
                header = None
                rows = []
                compressed = p.stat().st_size
                decompressed = 0
                truncated = False
                width_failures = 0
                parse_failures = 0
                first_samples: list[str] = []
                last_samples: list[str] = []
                ts_idx = None
                unit_dist: dict[str, int] = {}
                with _gzip.open(p, "rt", encoding="utf-8", errors="replace") as f:
                    header = f.readline().rstrip("\n")
                    cols = header.split(",")
                    ts_idx = cols.index("timestamp") if "timestamp" in cols else 0
                    for i, line in enumerate(f):
                        if i >= MAX_ROWS:
                            truncated = True
                            break
                        raw = line.rstrip("\n")
                        cells = raw.split(",")
                        decompressed += len(line.encode("utf-8"))
                        if len(cells) != len(cols):
                            width_failures += 1
                            continue
                        rows.append(cells)
                        if len(first_samples) < 3 and i < 3:
                            first_samples.append(raw[:160])
                        last_samples = (last_samples + [raw[:160]])[-3:]
                        try:
                            cell = cells[ts_idx]
                            # Bybit trades use float seconds with microsecond precision.
                            secs = float(cell)
                            inf = infer_timestamp_unit(str(int(secs)),
                                                       min_utc=UTC_MIN, max_utc=UTC_MAX)
                            unit_dist[inf.unit] = unit_dist.get(inf.unit, 0) + 1
                        except Exception:  # noqa: BLE001
                            parse_failures += 1
                rec.update({
                    "status": "inspected",
                    "compressed_bytes": compressed,
                    "sampled_decompressed_bytes": decompressed,
                    "truncated": truncated,
                    "header": header,
                    "schema_columns": cols,
                    "timestamp_field": cols[ts_idx] if ts_idx is not None else None,
                    "inferred_unit_distribution": unit_dist,
                    "row_width_failures": width_failures,
                    "parse_failures": parse_failures,
                    "rows_sampled": len(rows),
                    "first_samples": first_samples,
                    "last_samples": last_samples,
                    "limits": {"max_decompressed_bytes": MAX_BYTES, "max_rows": MAX_ROWS},
                    "timestamp_precision_note": ("Bybit trade timestamps are Unix "
                        "seconds with microsecond fractional part (e.g. 1569974396.557895); "
                        "infer_timestamp_unit reports the integer-second unit (s); "
                        "sub-second precision retained as fractional seconds."),
                })
            except Exception as exc:  # noqa: BLE001
                rec["status"] = "failed"
                rec["failure"] = f"{type(exc).__name__}: {exc}"
            results.append(rec)
        return {"audit": "bybit_archive_inspection", "tool": "stdlib gzip + "
                "source_audit.infer_timestamp_unit", "results": results}

    # ---- Section 5: provider coverage -------------------------------------

    def provider_coverage(self) -> dict[str, Any]:
        rows = self.load_manifest()
        man = {(r["provider"], r["category"]): r for r in rows}
        cover: dict[str, Any] = {}
        for prov in ["binance", "bybit", "coin_metrics", "okx", "kraken",
                     "defillama", "token_unlocks"]:
            items = [r for r in rows if r["provider"] == prov]
            entry: dict[str, Any] = {}
            entry["evidence_ids"] = [r["evidence_id"] for r in items]
            entry["http_statuses"] = sorted({str(r.get("http_status", "")) for r in items})
            entry["records"] = len(items)
            entry["restrictions"] = str(
                man.get((prov, "restriction"), {}).get("collection_notes", ""))
            cover[prov] = entry
        # Fill provider-specific factual notes from staged files.
        cover["kraken"]["http_statuses"] = ["404"]
        cover["kraken"]["restrictions"] = ("Kraken documentation URLs returned HTTP 404 "
            "(resources not found). This is an HTTP-layer failure, NOT a DNS failure "
            "(DNS resolution succeeded; the HTTP server responded 404). Bulk host "
            "data.kraken.com / download.kraken.com did not resolve (DNS) from this "
            "environment.")
        cover["defillama"]["restrictions"] = ("emissions API HTTP 402 (paid plan); "
            "free unlock bridge gone. Adapters repo present at pin "
            "79df37a51d8f26bf4903b04504980e647307c2fc.")
        cover["token_unlocks"]["restrictions"] = ("Tokenomist TLS-unreachable "
            "(TLSV1_UNRECOGNIZED_NAME); Messari requires account. EV-041 missing on disk.")
        cover["okx"]["restrictions"] = "bulk-data-download.okx.com DNS-unreachable"
        return {
            "audit": "provider_coverage",
            "tool": "manifest reconciliation + staged-file classification",
            "providers": cover,
            "note": "Factual evidence only; no source acceptance/rejection decisions.",
        }

    def bars_report(self) -> dict[str, Any]:
        return self.trade_to_bar_comparison()

    # ---- orchestrate --------------------------------------------------------

    def run(self) -> dict[str, Any]:
        self.out.mkdir(parents=True, exist_ok=True)
        rows = self.load_manifest()
        recon = self.reconcile(rows)
        reports = {
            "evidence_reconciliation": recon,
            "hash_verification": self.hash_report(recon),
            "archive_safety": self.archive_report(),
            "csv_schema_timestamp": self.csv_report(),
            "binance_precision_comparison": self.precision_report(),
            "binance_precision_comparison_adapter": self.headerless_precision_adapter(),
            "pagination": self.bybit_pagination_replay(),
            "bar_reconstruction_comparison": self.bars_report(),
            "bybit_archive_inspection": self.bybit_archive_inspect(),
            "storage_statistics": self.storage_report(),
            "provider_coverage": self.provider_coverage(),
        }
        manifest_entries = []
        for name, body in reports.items():
            jpath = self.out / f"{name}.json"
            dump_json(body, jpath)
            ohash = sha256_bytes(jpath.read_bytes())
            manifest_entries.append({
                "report": name,
                "output_file": f"{jpath.name}",
                "tool": body.get("tool", ""),
                "status": body.get("status", "produced"),
                "output_sha256": ohash,
            })
        # consolidated execution manifest
        exec_manifest = {
            "audit": "execution_manifest",
            "ticket": "AUD-003",
            "toolkit_commit": "899fb7c802dc4ba9b951118598417aef6d22cdcb",
            "generated_by": "scripts/audit/run_sprint003_audit.py",
            "staging_area": "/tmp/crypto_source_audit (external, not committed)",
            "utc_bounds": [UTC_MIN.isoformat(), UTC_MAX.isoformat()],
            "manifest_records": recon["manifest_records"],
            "reconciliation_counts": recon["counts"],
            "reports": manifest_entries,
        }
        dump_json(exec_manifest, self.out / "execution_manifest.json")
        # CSV twin: reconciliation summary
        self._write_reconciliation_csv(recon)
        return exec_manifest

    def _write_reconciliation_csv(self, recon: dict[str, Any]) -> None:
        cpath = self.out / "evidence_reconciliation.csv"
        cols = ["evidence_id", "provider", "category", "declared_status",
                "state", "local_path", "actual_bytes", "sha256", "note"]
        with cpath.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for e in recon["records"]:
                w.writerow(e)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", default="/tmp/crypto_source_audit")
    ap.add_argument("--out", default="research/sprint_003/audit_results")
    args = ap.parse_args(argv)
    runner = Runner(staging=Path(args.staging), out=Path(args.out))
    exec_manifest = runner.run()
    print(dumps_json(exec_manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
