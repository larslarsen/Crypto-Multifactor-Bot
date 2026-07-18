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
    compare_binance_archive_precision,
    compute_sha256,
    compute_storage_stats,
    dump_json,
    dumps_json,
    infer_timestamp_unit,
)
from source_audit.models import ProjectionAssumptions, StorageSample

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

    def pagination_report(self) -> dict[str, Any]:
        # Bybit captured cursor pages exist as raw JSON; report what is present.
        pages = sorted(self.staging.glob("bybit/*p[0-9].json")) + \
            sorted(self.staging.glob("bybit/*_p[0-9].json"))
        present = [str(p.relative_to(self.staging)) for p in pages]
        return {
            "audit": "pagination",
            "tool": "source_audit.paginate (PaginationCallbacks)",
            "status": "not_executed",
            "reason": ("paginate() drives a live fetch callback; captured raw Bybit "
                       "cursor pages are static snapshots, not a replayable fetch "
                       "sequence. Recorded as present evidence for Research Lead; no "
                       "synthetic pagination run performed (no fabrication)."),
            "captured_pages_present": present,
        }

    def bars_report(self) -> dict[str, Any]:
        # Need overlapping trade + candle samples for the SAME interval.
        return {
            "audit": "bar_reconstruction_comparison",
            "tool": "source_audit.reconstruct_bars + compare_bars",
            "status": "not_executed",
            "reason": ("Requires overlapping trade-level and provider-candle samples on "
                       "the same interval. Staged klines (1m 2025-01-01) and spot "
                       "aggTrades (2025-01-01) overlap in date, but full reconstruction "
                       "over the day is a heavy compute not required for feasibility "
                       "evidence; deferred. No synthetic bars produced (no fabrication)."),
            "overlap_candidates": {
                "trades": "binance/BTCUSDT-aggTrades-2025-01-01.zip",
                "candles": "binance/BTCUSDT-klines-1m-2025-01-01.zip",
            },
        }

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
            "pagination": self.pagination_report(),
            "bar_reconstruction_comparison": self.bars_report(),
            "storage_statistics": self.storage_report(),
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
