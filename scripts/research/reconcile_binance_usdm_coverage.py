#!/usr/bin/env python3
"""CEX-002 / Review 483: independent, read-only coverage reconciliation.

Only schema declarations are shared with the producer. Production identities are fixed;
there are deliberately no CLI flags for replacing pins or weakening checks. The private
_Policy injection exists solely for bounded fixtures in the accompanying test source.
Accepted cost descriptors and authenticated lineages establish accepted cost facts; cost
market-value Parquet files are never opened. Other products are scanned by timestamp only,
one symbol/month partition at a time. PASS artifacts are published only after every proof.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import re
import stat
import sys
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterator

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    QUALITY_GAP_COLUMNS,
    TYPED_GAP_MEMBERSHIP_COLUMNS,
    final_product_schema,
)

PREFIX = "binance_usdm_"
BAR, FLOW, OI, FUND, INDIC, BASIS, LIQ, COST, MEMBER, COVER = (
    PREFIX + name for name in (
        "bar_1h", "trade_flow_1h", "open_interest_5m", "funding_realized",
        "funding_indicative_1h", "mark_index_basis_1h", "liquidation_observed_daily",
        "cost_calibration", "perpetual_membership", "coverage_gap",
    )
)
TIMESTAMPS = {BAR: "open_time", FLOW: "open_time", OI: "create_time",
              FUND: "calc_time", INDIC: "open_time", BASIS: "open_time", LIQ: "event_time_ms"}
ALIGN = (BAR, OI, FUND, BASIS, LIQ)
SUMMARY = (BAR, FLOW, OI, FUND, INDIC, BASIS, LIQ, COST)
FIXED = {BAR: 24, FLOW: 24, OI: 288, INDIC: 24, BASIS: 24}
SCHEMAS = {
    "source_gap": final_product_schema(COVER),
    "typed_gap": pa.schema([c.field() for c in TYPED_GAP_MEMBERSHIP_COLUMNS]),
    "quality_gap": pa.schema([c.field() for c in QUALITY_GAP_COLUMNS]),
}
COMPONENTS = {"source_gap": "source_gap", "typed_gap": "typed_gap_membership", "quality_gap": "quality_gap"}
DIRECTORIES = {"source_gap": "source-gaps", "typed_gap": "typed-gaps", "quality_gap": "quality-gaps"}
CATEGORIES = {"completion", "coverage-summary", "daily", "daily-alignment", "excluded_membership",
              "quality-gaps-lineage", "quality_gap", "source-gaps-lineage", "source_gap",
              "summary", "typed-gaps-lineage", "typed_gap"}
REASONS = {
    "0": "no_observed_row_in_accepted_partition;source_availability_not_inferred",
    "1": "no_observed_settlement;expected_count_unknown",
    "2": "no_observed_liquidation_row;not_zero;source_censorship_retained",
    "3": "typed_source_unavailable",
    "4": "no_accepted_partition_observation;source_availability_unknown",
    "5": "partial_fixed_cadence_day;distinct_native_slot_count_incomplete",
    "6": "partial_fixed_cadence_day;duplicate_and_missing_native_slots",
    "7": "partial_fixed_cadence_day;irregular_native_interval",
    "8": "partial_fixed_cadence_day;distinct_native_slot_count_incomplete;irregular_native_interval",
    "9": "partial_fixed_cadence_day;duplicate_and_missing_native_slots;irregular_native_interval",
}
FIELD_ORDER = ["utc_date", "observed_counts", "observed_presence", "fixed_cadence_complete",
               "exclusion_reasons", "five_product_observed_intersection", "full_cadence_with_event_presence"]
SEMANTICS = {"funding_expected_count": None, "funding_absence": REASONS["1"],
             "liquidation": "observed_and_censored_never_complete", "availability": "unknown_not_a_causal_vintage",
             "fixed_daily_counts": FIXED}
ROOTS = (
    (MEMBER, "data/.cex002_perpetual_membership", "01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3"),
    (BAR, "data/.cex002_bar_1h", "3b803d3e84e5d0bf87064626cc0504e9ff92e225a53ba83cdd4e09c38a2e9fd7"),
    (FLOW, "data/.cex002_trade_flow_1h", "a165f9e57065514cadc95620c280a82dbad5032d17c19e1caf012c9d12a84d0a"),
    (OI, "data/.cex002_open_interest_5m", "bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4"),
    (FUND, "data/.cex002_funding_realized", "57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522"),
    (INDIC, "data/.cex002_price_state/" + INDIC, "360eb662ab89c47ca1f6db754b74f486a42de4aa116970221f0739268a51fba0"),
    (BASIS, "data/.cex002_price_state/" + BASIS, "b698c0543c281e3244e0c3358ea7ce1f347bc591b06a076058fed749d05584f0"),
    (LIQ, "data/.cex002_liquidation_observed_daily", "dc4127dccad31477cb72ec6fdf076dbdbdef34a1212d4f090d5f421b96dc267f"),
    (COST, "data/.cex002_cost_calibration", "fa4eced65e03e548cf5bf6500a9674a192a70dde9edf12d49c1f8bd539ad6f9e"),
)


@dataclass(frozen=True)
class _Policy:
    """Immutable production defaults; overrides are private fixture inputs, never CLI."""
    completion: str = "9e6e191b9ac1de05de4302e9e6dad64315f7e75d28ade638b977e28e68da1151"
    report: tuple[str, str] = ("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json", "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09")
    sizing: tuple[str, str] = ("research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json", "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589")
    holdout: tuple[str, str] = ("data/cex002_qualify/cex002_holdout_boundary.json", "2030e20aa5bd73df8fdbb7467e928508103b2e23659b85527101ec8b8546cb85")
    holdout_id: str = "c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2"
    holdout_utc: str = "2026-08-21T16:19:08.994166+00:00"
    source: tuple[str, str] = ("src/cryptofactors/ingest/binance_usdm_coverage.py", "6bb3788a91612d52fd204f9efc21a21e4a067eb679f387f16974915bcc501eee")
    roots: tuple[tuple[str, str, str], ...] = ROOTS
    # rows, actual partitions, row ceiling, partition ceiling, bytes, largest file
    bounds: tuple[tuple[str, tuple[int, ...]], ...] = (
        ("source_gap", (8317, 4817, 8317, 4817, 36831146, 9458)),
        ("typed_gap", (3742, 3742, 3742, 3742, 7757166, 2073)),
        ("quality_gap", (68220, 12465, 216934972, 130820, 9154761060, 418609)),
    )
    quality_rows: tuple[tuple[str, int], ...] = ((BAR, 154), (FLOW, 181), (OI, 57441), (INDIC, 1215), (BASIS, 4603), (LIQ, 4626))
    members: int = 771
    funding_only: int = 73
    excluded: int = 237
    cost_gaps: int = 494
    metadata_budget: int = 570896384
    metadata_release: int = 5556368003
    metadata_remainder: int = 4985471619
    page_bytes: int = 4096
    totals: tuple[int, int, int, int] = (64764, 1971447, 428090, 424431)
    example: tuple[str, str, int, int, str, int] = ("0GUSDT", "2025-09", 9, 8, "2025-09-22", 14)


class ReconciliationError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ReconciliationError(message)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def contract(schema: pa.Schema) -> list[dict[str, Any]]:
    return [{"name": f.name, "arrow_type": str(f.type), "nullable": f.nullable} for f in schema]


def schema_identity(name: str) -> str:
    value: Any = contract(SCHEMAS[name])
    if name == "source_gap":
        value = {"required_product": COVER, "schema": value}
        return sha((json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return sha(canonical(value))


def product_identity(product: str) -> str:
    value = {"required_product": product, "schema": contract(final_product_schema(product))}
    return sha((json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def native(symbol: str) -> dict[str, Any]:
    return {"venue": "BINANCE_USDM", "native_symbol": symbol, "canonical_instrument_id": None,
            "canonical_instrument_version_id": None, "reference_identity_state": "reference_identity_not_yet_created"}


def relative(value: Any) -> Path:
    require(type(value) is str and bool(value), "empty reference")
    require(not value.startswith("/") and "\\" not in value and "\0" not in value,
            "unsafe reference")
    require(all(x not in ("", ".", "..") for x in value.split("/")), "unsafe reference component")
    return Path(value)


def component(value: Any) -> str:
    require(type(value) is str and "/" not in value, "unsafe identity component")
    relative(value)
    return value


@contextmanager
def regular(path: Path) -> Iterator[Any]:
    """Open through held directory descriptors; never follow any symlink component."""
    path = path.absolute()
    require(".." not in path.parts, "unsafe absolute path")
    directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = None
    try:
        for part in path.parts[1:-1]:
            child = os.open(component(part), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(component(path.name), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        require(stat.S_ISREG(os.fstat(fd).st_mode), "input is not regular")
        with os.fdopen(fd, "rb") as stream:
            fd = None
            yield stream
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory)


def fingerprint(facts: os.stat_result) -> tuple[int, ...]:
    return facts.st_dev, facts.st_ino, facts.st_size, facts.st_mtime_ns, facts.st_ctime_ns


def hash_stream(stream: Any) -> str:
    stream.seek(0)
    digest = hashlib.sha256()
    while block := stream.read(2**20):
        digest.update(block)
    stream.seek(0)
    return digest.hexdigest()


def days(month: str) -> list[str]:
    require(type(month) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}", month) is not None, "invalid month")
    year, number = map(int, month.split("-"))
    require(1970 <= year <= 2100 and 1 <= number <= 12, "invalid month range")
    return [date(year, number, d).isoformat() for d in range(1, calendar.monthrange(year, number)[1] + 1)]


def months_between(first: str, last: str) -> list[str]:
    days(first)
    days(last)
    require(first <= last, "inverted reporting domain")
    y, m = map(int, first.split("-"))
    result = []
    while f"{y:04}-{m:02}" <= last:
        result.append(f"{y:04}-{m:02}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return result


def day_of(ms: int) -> str:
    require(type(ms) is int and ms >= 0, "invalid timestamp")
    return datetime.fromtimestamp(ms // 1000, UTC).date().isoformat()


def count(value: Any) -> int:
    require(type(value) is int and value >= 0, "invalid count")
    return value


class Checker:
    def __init__(self, repo: Path, output: Path, policy: _Policy):
        self.repo, self.output, self.p = repo.absolute(), output.absolute(), policy
        self.inventory: dict[str, dict[str, Any]] = {}
        self.snapshots: dict[Path, tuple[int, ...]] = {}
        self.metadata = Counter({key: 0 for key in CATEGORIES})
        self.inputs: dict[str, dict[str, Any]] = {}
        self.roots: dict[str, Path] = {}
        self.descriptor_roots: dict[str, Path] = {}
        self.index: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
        self.input_refs: set[Path] = set()
        self.max_partition = 0

    def authenticated(self, path: Path, digest: str, *, size: int | None = None,
                      category: str | None = None) -> None:
        require(re.fullmatch(r"[0-9a-f]{64}", digest or "") is not None, "invalid SHA-256 reference")
        with regular(path) as stream:
            before = os.fstat(stream.fileno())
            require(hash_stream(stream) == digest, f"digest mismatch: {path}")
            after = os.fstat(stream.fileno())
            require(fingerprint(before) == fingerprint(after), "input changed during hash")
        if size is not None:
            require(type(size) is int and before.st_size == size, "descriptor byte size mismatch")
        prior = self.snapshots.get(path)
        require(prior is None or prior == fingerprint(before), "input changed since authentication")
        self.snapshots[path] = fingerprint(before)
        if category is not None:
            rel = str(path.relative_to(self.output))
            require(rel not in self.inventory, "duplicate coverage reference")
            self.inventory[rel] = {"relative_path": rel, "sha256": digest, "size": before.st_size,
                                   "inode": before.st_ino, "mtime_ns": before.st_mtime_ns}
            if category != "parquet":
                require(category in CATEGORIES, "unknown metadata category")
                self.metadata[category] += before.st_size

    def json(self, path: Path, digest: str, *, size: int | None = None,
             category: str | None = None) -> dict[str, Any]:
        self.authenticated(path, digest, size=size, category=category)
        with regular(path) as stream:
            require(os.fstat(stream.fileno()).st_size <= 64 * 2**20, "JSON exceeds bound")
            body = stream.read(64 * 2**20 + 1)
            require(sha(body) == digest, "JSON changed after authentication")
        def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                require(key not in result, "duplicate JSON object key")
                result[key] = value
            return result
        value = json.loads(body, object_pairs_hook=unique_pairs)
        require(type(value) is dict, "JSON must be an object")
        return value

    def claim_input(self, product: str, descriptor: dict[str, Any]) -> tuple[Path, Path]:
        root = self.descriptor_roots[product]
        paths = tuple(root / relative(descriptor[key]) for key in ("parquet_path", "lineage_path"))
        for path in paths:
            require(path not in self.input_refs, "duplicate accepted input reference")
            self.input_refs.add(path)
        return paths  # type: ignore[return-value]

    def lineage(self, product: str, d: dict[str, Any]) -> dict[str, Any]:
        path = self.descriptor_roots[product] / relative(d["lineage_path"])
        value = self.json(path, d["lineage_sha256"], size=d.get("lineage_bytes"))
        for key in ("required_product", "native_symbol", "utc_month", "component", "row_count"):
            if key in value and (key == "required_product" or key in d):
                expected = product if key == "required_product" else d.get(key)
                require(value[key] == expected, f"accepted lineage identity mismatch: {key}")
        bound = value.get("parquet_sha256", value.get("quality_gap_parquet_sha256"))
        require(bound is None or bound == d["parquet_sha256"], "accepted lineage Parquet binding")
        for raw in value.get("raw_objects") or []:
            require(type(raw) is dict, "accepted lineage raw reference")
            require(raw.get("source_available_at") is None, "source availability must remain unknown")
            if "source_availability_state" in raw:
                require(raw["source_availability_state"] == "unknown_not_imputed", "source availability state")
        return value

    def parquet_rows(self, path: Path, digest: str, schema: pa.Schema, row_count: int,
                     *, columns: list[str] | None = None) -> Iterator[dict[str, Any]]:
        """All newly read facts are covered by a full-file hash on the same held fd."""
        with regular(path) as stream:
            start = os.fstat(stream.fileno())
            require(hash_stream(stream) == digest, "Parquet digest mismatch")
            parquet = pq.ParquetFile(stream)
            require(parquet.schema_arrow.equals(schema, check_metadata=False), "physical Arrow schema mismatch")
            require(parquet.metadata.num_rows == row_count, "physical row count mismatch")
            seen = 0
            for batch in parquet.iter_batches(batch_size=8192, columns=columns, use_threads=False):
                for row in batch.to_pylist():
                    seen += 1
                    yield row
            require(seen == row_count, "streamed row count mismatch")
            require(hash_stream(stream) == digest and fingerprint(os.fstat(stream.fileno())) == fingerprint(start),
                    "Parquet changed during read")
            prior = self.snapshots.get(path)
            require(prior is None or prior == fingerprint(start), "Parquet changed since authentication")
            self.snapshots[path] = fingerprint(start)

    def authorities(self) -> None:
        p = self.p
        report = self.json(self.repo / relative(p.report[0]), p.report[1])
        sizing = self.json(self.repo / relative(p.sizing[0]), p.sizing[1])
        holdout = self.json(self.repo / relative(p.holdout[0]), p.holdout[1])
        self.authenticated(self.repo / relative(p.source[0]), p.source[1])
        require((holdout["boundary_id"], holdout["boundary_utc"]) == (p.holdout_id, p.holdout_utc), "holdout binding")
        self.report = report
        self.sizing = sizing
        self.c = self.json(self.output / ".complete" / (p.completion + ".json"), p.completion, category="completion")
        c = self.c
        require(c["document_type"] == "binance_usdm_coverage_gap_product_completion" and c["schema_version"] == 1
                and c["required_product"] == COVER, "coverage completion identity")
        require(c["normalizer_source_sha256"] == p.source[1], "producer source identity")
        require(set(c["components"]) == set(COMPONENTS.values()) | {
            "cost_normalization_source_gap_reference", "fee_authority_gap_reference"}, "exact coverage component set")
        require(c["authorities"] == {"report_sha256": p.report[1], "sizing_sha256": p.sizing[1],
                "holdout_sha256": p.holdout[1], "holdout_boundary_id": p.holdout_id, "holdout_utc": p.holdout_utc}, "coverage authority binding")
        require(c["input_completions"] == {name: {"completion_sha256": digest} for name, _, digest in p.roots}, "input completion binding")
        for product, path, digest in p.roots:
            root = self.repo / relative(path)
            self.roots[product] = root
            self.descriptor_roots[product] = root.parent if product in (INDIC, BASIS) else root
            self.inputs[product] = self.json(root / ".complete" / (digest + ".json"), digest)
            require(sorted(x.name for x in (root / ".complete").iterdir()) == [digest + ".json"], "input completion is not sole")
            value = self.inputs[product]
            require(value["required_product"] == product and type(value["partitions"]) is list, "accepted completion identity")
            if product != COST:
                require(value["schema_sha256"] == product_identity(product), "accepted schema identity")
                if "schema" in value:
                    require(value["schema"] == contract(final_product_schema(product)), "accepted schema contract")
        alloc = sizing["coverage_authority"]
        for name, bound in p.bounds:
            key = COMPONENTS[name] + "_component"
            a = alloc[key]
            require(a["schema"] == contract(SCHEMAS[name]), "sizing schema binding")
            require((a["projected_rows"], a["partition_count"], a["projected_bytes"], a["largest_partition_bytes"])
                    == (bound[2], bound[3], bound[4], bound[5]), "sizing allocation binding")
        require(sizing["capacity"]["catalog_manifest_bundle_bytes"] == p.metadata_release
                and sizing["partitioning"]["catalog_page_bytes"] == p.page_bytes, "sizing metadata binding")
        require(sum(v[3] for _, v in p.bounds) * p.page_bytes == p.metadata_budget
                and p.metadata_release - p.metadata_budget == p.metadata_remainder, "frozen reservation equation")

    def membership_and_source(self) -> None:
        rows = self.report["membership"]["classifications"]
        require(type(rows) is list and all(type(r) is dict for r in rows), "membership classifications")
        names = [component(r["symbol"]) for r in rows]
        require(len(names) == len(set(names)), "duplicate classified identity")
        accepted = [r for r in rows if r["accepted"] is True]
        rejected = [r for r in rows if r["accepted"] is not True]
        self.members = sorted(r["symbol"] for r in accepted)
        self.accepted = {r["symbol"]: r for r in accepted}
        self.rejected = rejected
        require(len(accepted) == self.p.members and len(rejected) == self.p.excluded, "membership allocation")
        funding_only = set()
        for r in accepted:
            require(r["membership_class"] == "confirmed_perpetual", "accepted membership classification")
            evidence = r["evidence"]
            require(type(evidence) is list and bool(evidence), "membership evidence absent")
            terms = {k: {e[k] for e in evidence if e.get(k) not in (None, "")} for k in
                     ("contract_type", "base_asset", "quote_asset", "margin_asset")}
            require(all(len(values) <= 1 for values in terms.values()), "conflicting membership evidence")
            if not all(terms.values()):
                require(evidence[0]["kind"] == "official_realized_funding_observation"
                        and evidence[0]["semantics"] == "only a perpetual contract realizes funding", "funding-only authority class")
                require("monthly/fundingRate" in evidence[0]["families"], "funding-only family evidence")
                funding_only.add(r["symbol"])
        require(len(funding_only) == self.p.funding_only, "funding-only identity set")
        self.funding_only = funding_only
        completion = self.inputs[MEMBER]
        require((completion["membership_rows"], completion["funding_only_rows"], completion["detailed_metadata_rows"], completion["excluded_classifications"])
                == (len(accepted), len(funding_only), len(accepted) - len(funding_only), len(rejected)), "membership completion counts")
        found = []
        for d in completion["partitions"]:
            symbol = component(d["native_symbol"])
            found.append(symbol)
            require(symbol in self.accepted and d["row_count"] == 1, "membership descriptor identity")
            path, _ = self.claim_input(MEMBER, d)
            lineage = self.lineage(MEMBER, d)
            require(lineage["classification_sha256"] == sha(canonical(self.accepted[symbol])), "membership classification binding")
            rr = list(self.parquet_rows(path, d["parquet_sha256"], final_product_schema(MEMBER), 1))[0]
            require(all(rr[k] == v for k, v in native(symbol).items()), "membership native identity")
            require((rr["contract_metadata_state"] == "funding_only_terms_unavailable") == (symbol in funding_only), "membership metadata class")
        require(found == self.members, "complete sorted membership identity set")
        require(self.c["membership"] == {"accepted_identities": len(accepted), "funding_only_identities": len(funding_only),
                "excluded_classifications": len(rejected), "product_absence_removes_membership": False}, "coverage membership binding")
        self.sources: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self.typed: set[tuple[str, str]] = set()
        field_map = {"family_group": "family_group", "gap_kind": "kind", "gap_status": "status",
                     "first_observed_period": "first_observed", "last_observed_period": "last_observed",
                     "family_first_observed_period": "family_first_observed", "family_last_observed_period": "family_last_observed",
                     "onboard_period": "onboard_period", "close_period": "close_period", "explained_by": "explained_by"}
        for matrix in self.report["product_matrix"]:
            product = component(matrix["product"])
            for gap in matrix.get("universe_coverage_gaps", []):
                symbol = component(gap["symbol"])
                require(symbol in self.accepted, "source gap nonmember")
                record = {**native(symbol), "required_product": product,
                          **{k: str(gap.get(v) or "") for k, v in field_map.items()},
                          "blocking": bool(gap.get("blocking")), "families": list(gap.get("families") or []),
                          "missing_months": list(gap.get("missing_months") or [])}
                record["family_count"] = len(record["families"])
                for key in ("observed_months", "missing_month_count", "objects"):
                    record[key] = None if gap.get(key) is None else int(gap[key])
                self.sources[product, symbol].append(record)
            for symbol in matrix.get("typed_gap_symbols", []):
                key = (product, component(symbol))
                require(symbol in self.accepted and key not in self.typed, "duplicate/nonmember typed gap")
                self.typed.add(key)
        bounds = dict(self.p.bounds)
        require(sum(map(len, self.sources.values())) == bounds["source_gap"][0]
                and len(self.sources) == bounds["source_gap"][1] and len(self.typed) == bounds["typed_gap"][0], "report gap allocation")

    def accepted_index(self) -> None:
        for product in TIMESTAMPS:
            entries = {}
            for d in self.inputs[product]["partitions"]:
                key = (component(d["native_symbol"]), d["utc_month"])
                days(key[1])
                require(key[0] in self.accepted and key not in entries, "duplicate/nonmember accepted partition")
                count(d["row_count"])
                self.claim_input(product, d)
                entries[key] = d
            self.index[product] = entries
        # Establish the complete domain independently of the coverage documents.
        domain = {m for entries in self.index.values() for _, m in entries}
        for records in self.sources.values():
            for r in records:
                for k in ("first_observed_period", "last_observed_period", "family_first_observed_period",
                          "family_last_observed_period", "onboard_period", "close_period"):
                    if r[k]:
                        days(r[k])
                        domain.add(r[k])
        for r in self.accepted.values():
            for e in r["evidence"]:
                for k in ("onboard_ms", "closed_observed_ms"):
                    if e.get(k) is not None:
                        domain.add(day_of(e[k])[:7])
        require(bool(domain), "empty historical domain")
        self.months = months_between(min(domain), max(domain))
        expected = {"first_utc_month": self.months[0], "last_utc_month": self.months[-1], "month_count": len(self.months),
                    "basis": "accepted_source_membership_bounds_and_actual_product_ranges"}
        require(self.c["alignment"]["historical_domain"] == expected, "historical calendar domain")
        self.row_equations()

    def row_equations(self) -> None:
        equations = {n: v.get("row_equation", v.get("totals", v.get("source_equation"))) for n, v in self.inputs.items()}
        require(self.c["row_equations"] == equations, "completion row-equation binding")
        for n in (BAR, FLOW):
            r = equations[n]
            require(r["physical_rows"] == r["product_rows"] + r["excluded_rows"] + r["collapsed_rows"]
                    and r["duplicate_rows"] == r["overlap_rows"] == 0, "bar/flow row equation")
        for n, collapsed in ((OI, "collapsed_identical_source_rows"), (FUND, "collapsed_identical_rows"), (LIQ, "collapsed_identical_rows")):
            r = equations[n]
            require(r["physical_source_rows"] == r["product_rows"] + r["excluded_source_rows"] + r[collapsed], "accepted source-row equation")
        require(equations[FUND]["inferred_events"] == equations[FUND]["conflicting_events"] == 0, "funding event semantics")
        require(equations[LIQ]["inclusive_requested_slots"] == equations[LIQ]["product_rows"] + equations[LIQ]["missing_daily_slots"]
                and equations[LIQ]["imputed_rows"] == 0, "liquidation request/censorship semantics")
        for n, factor in ((INDIC, 1), (BASIS, 3)):
            r = equations[n]
            require(r["physical_source_rows"] == r["joined_input_rows"] + r["unjoinable_source_rows"] + r["excluded_source_rows"] + r["collapsed_identical_rows"]
                    and r["joined_input_rows"] == factor * r["product_rows"] and r["fabricated_rows"] == 0, "price-state equation")
        for n in TIMESTAMPS:
            require(sum(d["row_count"] for d in self.index[n].values()) == equations[n]["product_rows"], "accepted descriptor row sum")
        r = equations[MEMBER]
        require(r["classifications"] == r["accepted_membership_rows"] + r["excluded_classifications"], "membership equation")
        r = equations[COST]
        require(r["objects"] == r["generation0_objects"] + r["recovery_objects"]
                and r["physical_rows"] == r["retained_rows"] + r["deduplicated_rows"] + r["dropped_rows"], "cost equation")

    def quality_authority(self) -> None:
        """Stream accepted quality evidence into bounded per-partition digest records."""
        self.quality: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.quality_missing: Counter[tuple[str, str]] = Counter()
        self.quality_product_rows: Counter[str] = Counter()
        for product in TIMESTAMPS:
            c = self.inputs[product]
            descriptors = ([c["quality_gap_artifact"]] if c.get("quality_gap_artifact") is not None else [])
            descriptors += c.get("quality_gap_artifacts", [])
            if product == LIQ:
                descriptors += [d for d in c["gaps"] if d.get("kind") != "coinalyze_symbol_unmapped"]
            for d in descriptors:
                path, _ = self.claim_input(product, d)
                lineage = self.lineage(product, d)
                current = None
                digest = None
                rows = 0
                start = 0
                def finish(end: int) -> None:
                    if current is not None:
                        require(current not in self.quality, "repeated quality partition")
                        self.quality[current] = {"rows": rows, "rows_sha256": digest.hexdigest(),
                            "upstream": [{"descriptor_sha256": sha(canonical(d)), "parquet_sha256": d["parquet_sha256"],
                            "lineage_sha256": d["lineage_sha256"], "first_source_row_ordinal": start,
                            "last_source_row_ordinal": end, "source_row_count": end - start + 1}]}
                for ordinal, row in enumerate(self.parquet_rows(path, d["parquet_sha256"], SCHEMAS["quality_gap"], d["row_count"])):
                    key = (row["required_product"], row["native_symbol"], row["utc_month"])
                    require(key[0] == product and key[1] in self.accepted, "quality authority identity")
                    for i, name in enumerate(("required_product", "native_symbol", "utc_month")):
                        if name in lineage:
                            require(lineage[name] == key[i], "quality authority lineage identity")
                    days(key[2])
                    count(row["expected_grid_count"])
                    a, b = row["missing_run_start_ms"], row["missing_run_end_ms"]
                    require((a is None and b is None) or (type(a) is int and type(b) is int and a <= b), "quality endpoints")
                    if key != current:
                        require(current is None or current < key, "quality source ordering")
                        finish(ordinal - 1)
                        current, start, rows, digest = key, ordinal, 0, hashlib.sha256()
                    digest.update(canonical(row))
                    rows += 1
                    self.quality_missing[product, key[1]] += row["expected_grid_count"]
                    self.quality_product_rows[product] += 1
                finish(d["row_count"] - 1)
        require(dict(self.quality_product_rows) == dict(self.p.quality_rows), "quality product row counts")

    def manifests_and_gaps(self) -> None:
        require(set(self.c["manifests"]) == {"source_gap", "typed_gap", "quality_gap", "daily", "summary", "excluded_membership"}, "exact six manifests")
        self.manifests = {}
        for name, d in self.c["manifests"].items():
            path = self.output / relative(d["path"])
            require(str(path.relative_to(self.output)) == f".manifests/{d['sha256']}.json", "manifest content-addressed path")
            m = self.json(path, d["sha256"], size=d["bytes"], category=name)
            require(m["document_type"] == f"binance_usdm_coverage_{name}_manifest" and m["schema_version"] == 1,
                    "manifest identity")
            require(type(m["rows"]) is list and m["row_count"] == len(m["rows"]), "manifest row count")
            self.manifests[name] = m["rows"]
        require(self.manifests["excluded_membership"] == self.rejected, "excluded classification evidence")
        self.quality_refs: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self.component_facts = {}
        for name, bounds in self.p.bounds:
            seen = []
            rows = total_bytes = largest = 0
            for d in self.manifests[name]:
                product, symbol = component(d["required_product"]), component(d["native_symbol"])
                require(symbol in self.accepted, "coverage gap nonmember")
                month = d["utc_month"] if name == "quality_gap" else "authority"
                if name == "quality_gap":
                    days(month)
                key = (product, symbol, month)
                seen.append(key)
                directory = DIRECTORIES[name]
                path = self.output / f".{directory}/{product}/{symbol}/{month}/{d['parquet_sha256']}.parquet"
                linpath = self.output / f".{directory}-lineage/{product}/{symbol}/{month}/{d['lineage_sha256']}.json"
                self.authenticated(path, d["parquet_sha256"], size=d["parquet_bytes"], category="parquet")
                lineage = self.json(linpath, d["lineage_sha256"], size=d["lineage_bytes"], category=directory + "-lineage")
                require(lineage["document_type"] == f"binance_usdm_coverage_{directory}_lineage" and lineage["schema_version"] == 1,
                        "coverage lineage identity")
                require((lineage["component"], lineage["required_product"], lineage["native_symbol"], lineage["utc_month"],
                         lineage["row_count"], lineage["parquet_sha256"], lineage["schema"])
                        == (directory, product, symbol, month, d["row_count"], d["parquet_sha256"], contract(SCHEMAS[name])), "coverage lineage contract")
                actual = list(self.parquet_rows(path, d["parquet_sha256"], SCHEMAS[name], count(d["row_count"])))
                if name == "source_gap":
                    require(actual == self.sources.get((product, symbol)), "qualification source gap rows")
                    require(lineage["upstream"] == [{"report_sha256": self.p.report[1], "rows_sha256": sha(canonical(actual))}], "source gap lineage authority")
                elif name == "typed_gap":
                    require((product, symbol) in self.typed and actual == [{**native(symbol), "required_product": product}], "typed membership rows")
                    require(lineage["upstream"] == [{"report_sha256": self.p.report[1], "row_sha256": sha(canonical({"required_product": product, "native_symbol": symbol}))}], "typed lineage authority")
                else:
                    expected = self.quality.get(key)
                    require(expected is not None and len(actual) == expected["rows"]
                            and sha(b"".join(canonical(r) for r in actual)) == expected["rows_sha256"]
                            and lineage["upstream"] == expected["upstream"], "quality gap upstream rows/lineage")
                    self.quality_refs[product, symbol].append({k: d[k] for k in ("utc_month", "row_count", "parquet_sha256", "parquet_bytes", "lineage_sha256", "lineage_bytes")})
                rows += len(actual)
                total_bytes += d["parquet_bytes"]
                largest = max(largest, d["parquet_bytes"])
            expected_keys = ([(a, b, "authority") for a, b in sorted(self.sources)] if name == "source_gap" else
                             [(a, b, "authority") for a, b in sorted(self.typed)] if name == "typed_gap" else list(self.quality))
            require(seen == expected_keys and len(seen) == len(set(seen)), "gap partition keys/order/completeness")
            require((rows, len(seen)) == bounds[:2] and rows <= bounds[2] and len(seen) <= bounds[3]
                    and total_bytes <= bounds[4] and largest <= bounds[5], "gap component allocation bounds")
            value = self.c["components"][COMPONENTS[name]]
            expected = {"schema_sha256": schema_identity(name), "rows": rows, "partitions": len(seen),
                        "parquet_bytes": total_bytes, "largest_file_bytes": largest, "bound_bytes": bounds[4],
                        "largest_file_bound_bytes": bounds[5], "manifest_sha256": self.c["manifests"][name]["sha256"]}
            expected.update({"row_ceiling": bounds[2], "partition_ceiling": bounds[3]} if name == "quality_gap" else {"partition_bound": bounds[3]})
            require(value == expected, "component measured facts/schema/bounds")
            self.component_facts[name] = expected
        for refs in self.quality_refs.values():
            refs.sort(key=lambda r: (r["utc_month"], r["parquet_sha256"]))

    def cost(self) -> None:
        c = self.inputs[COST]
        require(c["fee_authority"]["gap_rows"] == self.p.members and c["fee_authority"]["official_historical_rows"] == 0
                and c["fee_authority"]["missing_fee_is_zero"] is False
                and c["scenario_policy"]["rows"] == 2 and c["scenario_policy"]["historical_observation"] is False
                and c["scenario_policy"]["historical_upper_bound"] is False, "cost fee/scenario semantics")
        require(c["scenario_policy"]["charges_each_side"] is True
                and c["scenario_policy"]["authority_class"] == "ASSUMED_CONSERVATIVE"
                and datetime.fromisoformat(c["scenario_policy"]["policy_known_at"].replace("Z", "+00:00"))
                > datetime.fromisoformat(self.p.holdout_utc), "scenario policy may not be backdated")
        frozen = c["frozen_source_gaps"]
        gap = self.json(self.roots[COST] / relative(frozen["path"]), frozen["sha256"], size=frozen["bytes"])
        require(len(gap["gaps"]) == frozen["row_count"] == self.p.cost_gaps, "cost source gaps")
        require(all(g["symbol"] in self.accepted for g in gap["gaps"]), "cost source-gap member set")
        require(self.c["components"]["cost_normalization_source_gap_reference"] == {
            "rows": frozen["row_count"], "sha256": frozen["sha256"], "bytes": frozen["bytes"], "copied": False,
            "semantics": "accepted_normalization_source_gaps_distinct_from_qualification_source_gaps"}, "cost gap reference")
        require(self.c["components"]["fee_authority_gap_reference"] == {"rows": self.p.members, "copied": False,
            "completion_sha256": dict((n, h) for n, _, h in self.p.roots)[COST],
            "semantics": "historical_fee_schedule_unavailable;not_zero_cost"}, "fee gap reference")
        self.cost_by_symbol: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
        fee_members = []
        scenarios = 0
        schema_artifacts = 0
        component_rows = Counter()
        seen = set()
        for d in c["partitions"]:
            key = (component(d["component"]), component(d["native_symbol"]), component(d["utc_month"]))
            require(key not in seen, "duplicate cost descriptor")
            seen.add(key)
            count(d["row_count"])
            self.claim_input(COST, d)
            lineage = self.lineage(COST, d)
            component_rows[key[0]] += d["row_count"]
            if key[1] in self.accepted:
                # Preserve only the authenticated facts consumed by the summary, not
                # whole accepted lineages or any cost market-value columns.
                source_days = [{"economic_day": raw["economic_day"]} for raw in lineage.get("raw_objects") or []
                               if raw.get("economic_day") is not None]
                self.cost_by_symbol[key[1]].append((d, {"raw_objects": source_days}))
            if key[0] == "fee_authority_gap":
                require(d["row_count"] == 1 and key[1] in self.accepted, "fee gap identity")
                fee_members.append(key[1])
            elif key[0] == "scenario_policy":
                require(key[1:] == ("BINANCE_USDM", "configuration"), "scenario scope")
                scenarios += d["row_count"]
            elif key[0] == "official_fee_schedule":
                require(key[1:] == ("__schema__", "schema") and d["row_count"] == 0,
                        "historical fee schema is not an observation")
                schema_artifacts += 1
            else:
                require(key[0] in {"retained_book_depth", "retained_book_ticker"}, "foreign cost component")
                require(key[1] in self.accepted, "cost descriptor nonmember")
        require(sorted(fee_members) == self.members and len(fee_members) == len(set(fee_members)) and scenarios == 2,
                "exact fee/policy descriptor sets")
        require(schema_artifacts == 1, "sole historical fee schema descriptor")
        require(all(component_rows[k] == v for k, v in c["component_rows"].items())
                and set(component_rows) <= set(c["component_rows"]), "accepted cost component descriptor rows")
        self.cost_component_rows = dict(component_rows)

    def scan(self, product: str, symbol: str, month: str) -> dict[str, Any]:
        d = self.index[product].get((symbol, month))
        result: dict[str, Any] = {"counts": Counter(), "complete": {}, "failures": {}, "first": None, "last": None, "duplicates": 0}
        if d is None:
            return result
        self.lineage(product, d)
        path = self.descriptor_roots[product] / relative(d["parquet_path"])
        column = TIMESTAMPS[product]
        slots: dict[str, set[int]] = defaultdict(set)
        for row in self.parquet_rows(path, d["parquet_sha256"], final_product_schema(product), d["row_count"], columns=[column]):
            timestamp = row[column]
            day = day_of(timestamp)
            require(day[:7] == month, "timestamp escapes partition month")
            result["counts"][day] += 1
            slots[day].add(timestamp)
            result["first"] = timestamp if result["first"] is None else min(result["first"], timestamp)
            result["last"] = timestamp if result["last"] is None else max(result["last"], timestamp)
        for day, timestamps in slots.items():
            duplicate = result["counts"][day] - len(timestamps)
            result["duplicates"] += duplicate
            if product in FIXED:
                ordered = sorted(timestamps)
                spacing = 300000 if product == OI else 3600000
                regular_spacing = all(b - a == spacing for a, b in zip(ordered, ordered[1:]))
                expected = FIXED[product]
                result["complete"][day] = len(timestamps) == expected and regular_spacing
                if not result["complete"][day]:
                    incomplete = len(timestamps) != expected
                    missing_with_duplicates = duplicate > 0 and len(timestamps) < expected
                    result["failures"][day] = ((9 if missing_with_duplicates else 8) if incomplete and not regular_spacing else
                                               (6 if missing_with_duplicates else 5) if incomplete else 7)
        self.max_partition = max(self.max_partition, d["row_count"])
        return result

    def absent_reason(self, product: str, symbol: str, month: str) -> int:
        if (symbol, month) in self.index[product]:
            return 1 if product == FUND else 2 if product == LIQ else 0
        return 3 if (product, symbol) in self.typed else 4

    def daily_and_summaries(self) -> None:
        daily = self.manifests["daily"]
        summaries = self.manifests["summary"]
        expected_keys = [(s, m) for s in self.members for m in self.months]
        require([(d["native_symbol"], d["utc_month"]) for d in daily] == expected_keys, "complete sorted unique daily matrix")
        require([d["native_symbol"] for d in summaries] == self.members, "complete sorted unique summary member set")
        digests = [hashlib.sha256() for _ in range(3)]
        totals = [0, 0, 0, 0]
        example_result = None
        for si, symbol in enumerate(self.members):
            facts = {p: {"observed_count": 0, "first_observed_ms": None, "last_observed_ms": None,
                         "duplicate_timestamps": 0, "input_descriptors": []} for p in TIMESTAMPS}
            for mi, month in enumerate(self.months):
                scans = {}
                for product in TIMESTAMPS:
                    scan = self.scan(product, symbol, month)
                    if product in ALIGN:
                        scans[product] = scan
                    d = self.index[product].get((symbol, month))
                    if d is not None:
                        f = facts[product]
                        f["observed_count"] += d["row_count"]
                        f["duplicate_timestamps"] += scan["duplicates"]
                        if scan["first"] is not None:
                            f["first_observed_ms"] = scan["first"] if f["first_observed_ms"] is None else min(f["first_observed_ms"], scan["first"])
                            f["last_observed_ms"] = scan["last"] if f["last_observed_ms"] is None else max(f["last_observed_ms"], scan["last"])
                        f["input_descriptors"].append({"utc_month": month, "descriptor_sha256": sha(canonical(d)),
                            "parquet_sha256": d["parquet_sha256"], "lineage_sha256": d["lineage_sha256"]})
                descriptor = daily[si * len(self.months) + mi]
                report = self.json(self.output / f".daily/{symbol}/{month}/{descriptor['sha256']}.json",
                                   descriptor["sha256"], size=descriptor["bytes"], category="daily-alignment")
                require(report["document_type"] == "binance_usdm_coverage_daily_alignment" and report["schema_version"] == 1
                        and (report["native_symbol"], report["utc_month"]) == (symbol, month), "daily identity")
                require(report["field_order"] == FIELD_ORDER and report["product_order"] == list(ALIGN)
                        and report["exclusion_reason_dictionary"] == REASONS and report["semantics"] == SEMANTICS, "daily semantic contract")
                require(type(report["days"]) is list and all(type(r) is list and len(r) == 7 for r in report["days"]), "daily row shape")
                require([r[0] for r in report["days"]] == days(month), "complete sorted unique UTC calendar")
                observed = full = 0
                for row in report["days"]:
                    day = row[0]
                    counts = [scans[p]["counts"].get(day, 0) for p in ALIGN]
                    presence = [n > 0 for n in counts]
                    complete = [scans[BAR]["complete"].get(day, False), scans[OI]["complete"].get(day, False), None,
                                scans[BASIS]["complete"].get(day, False), None]
                    reasons = [self.absent_reason(p, symbol, month) if not presence[i] else
                               scans[p]["failures"].get(day) if p in FIXED and not complete[i] else None for i, p in enumerate(ALIGN)]
                    intersection = all(presence)
                    cadence = all(complete[i] is True for i in (0, 1, 3)) and presence[2] and presence[4]
                    expected = [day, counts, presence, complete, reasons, intersection, cadence]
                    # Canonical equality also rejects 0/1 in place of booleans and null event completeness.
                    require(canonical(row) == canonical(expected), "daily independent counts/presence/cadence/exclusion predicate")
                    encoded = canonical([symbol, row])
                    digests[0].update(encoded)
                    if intersection:
                        digests[1].update(encoded)
                        observed += 1
                    if cadence:
                        digests[2].update(encoded)
                        full += 1
                measured = {"days": len(report["days"]), "five_product_observed_intersection": observed,
                            "full_cadence_with_event_presence": full}
                require(report["counts"] == measured and all(descriptor[k] == v for k, v in measured.items()), "daily/manifest count reconciliation")
                totals = [totals[0] + 1, totals[1] + measured["days"], totals[2] + observed, totals[3] + full]
                es, em, eo, ef, ed, eb = self.p.example
                if (symbol, month) == (es, em):
                    basis_count = scans[BASIS]["counts"].get(ed, 0)
                    require((observed, full, basis_count) == (eo, ef, eb), "bounded reference example")
                    example_result = {"native_symbol": es, "utc_month": em, "observed_days": observed,
                                      "full_cadence_days": full, "basis_date": ed, "basis_rows": basis_count}
            d = summaries[si]
            summary = self.json(self.output / f".summary/{symbol}/{d['sha256']}.json", d["sha256"], size=d["bytes"], category="coverage-summary")
            self.summary(symbol, summary, facts)
        require(example_result is not None, "reference example missing")
        require(tuple(totals) == self.p.totals, "global measured counts differ from pinned facts")
        a = self.c["alignment"]
        require((a["daily_report_partitions"], a["aligned_day_rows"], a["five_product_observed_day_count"], a["full_cadence_day_count"])
                == tuple(totals), "alignment global counts")
        require((a["aligned_days_sha256"], a["five_product_observed_day_sha256"], a["full_cadence_day_sha256"])
                == tuple(h.hexdigest() for h in digests), "canonical symbol/day digests")
        require(a["daily_report_equation"] == {"accepted_membership_identities": len(self.members), "historical_utc_months": len(self.months),
                "expected_partitions": len(expected_keys), "published_partitions": len(daily)}, "daily matrix equation")
        require(a["maximum_loaded_symbol_month_observations"] == self.max_partition and a["funding_expected_count"] is None
                and a["liquidation_complete"] is False, "alignment boundedness/event semantics")
        for name in ("daily", "summary"):
            require(a[name + "_manifest_sha256"] == self.c["manifests"][name]["sha256"], "alignment manifest binding")
        self.alignment_facts = {"counts": totals, "digests": [h.hexdigest() for h in digests], "reference_example": example_result,
                                "maximum_timestamp_partition_rows": self.max_partition}

    def summary(self, symbol: str, document: dict[str, Any], facts: dict[str, Any]) -> None:
        require(document["document_type"] == "binance_usdm_instrument_coverage_summary" and document["schema_version"] == 1,
                "summary identity")
        require(all(document[k] == v for k, v in native(symbol).items()), "summary native identity")
        require(document["reporting_domain"] == {"first_utc_month": self.months[0], "last_utc_month": self.months[-1]}, "summary domain")
        entries = document["products"]
        require(type(entries) is list and [e["required_product"] for e in entries] == list(SUMMARY), "summary exact product order/set")
        for entry in entries:
            product = entry["required_product"]
            if product != COST:
                f = facts[product]
                require(all(entry[k] == v for k, v in f.items()), "summary accepted input rows/extrema/duplicates/descriptors")
                missing = self.quality_missing[product, symbol]
                established = f["observed_count"] > 0 or missing > 0
                countable = established and (product in FIXED or product == LIQ)
                require(entry["expected_count"] == (f["observed_count"] + missing if countable else None)
                        and entry["missing_count"] == (missing if countable else None), "summary expected/missing counts")
                basis = ("accepted_observed_rows_plus_normalized_quality_gap_expected_grid_count" if countable and product in FIXED else
                         "authenticated_inclusive_request_calendar;never_a_completeness_claim" if countable else None)
                require(entry["expected_count_basis"] == basis, "summary count basis")
                require(entry["component_counts"] is None and entry["source_day_extrema"] is None
                        and entry["non_instrument_cost_counts"] is None and entry["fee_authority_gap_reference"] is None,
                        "non-cost summary fields")
            else:
                self.cost_summary(symbol, entry)
            precision = ("source_day_only_event_extrema_unavailable" if product == COST else
                         "millisecond_native_five_minute_phase" if product == OI else
                         "millisecond_observed_event" if product == FUND else
                         "millisecond_observed_daily_point" if product == LIQ else "millisecond_hour_open")
            require(entry["time_precision"] == precision and entry["observed_count_unit"] ==
                    ("unavailable_per_instrument;component_counts_only" if product == COST else "normalized_rows"), "summary count/time units")
            source_rows = self.sources.get((product, symbol), [])
            hashes = sorted(sha(canonical(r)) for r in source_rows)
            contexts = []
            for r in source_rows:
                contexts.append({"row_sha256": sha(canonical(r)), **{k: r[k] for k in ("gap_kind", "gap_status", "first_observed_period",
                    "last_observed_period", "family_first_observed_period", "family_last_observed_period", "onboard_period", "close_period", "missing_months")},
                    "semantics": "qualification_gap_context;not_a_current_missing_observation"})
            require(entry["source_gap_row_sha256"] == hashes and entry["qualification_source_gap_context"] == sorted(contexts, key=lambda r: r["row_sha256"]),
                    "summary qualification references")
            require(entry["quality_gap_partitions"] == self.quality_refs.get((product, symbol), []), "summary quality references")
            require(entry["source_revisions"] == "retained_in_referenced_partition_lineages;no_availability_vintage_inferred", "revision/availability semantics")

    def cost_summary(self, symbol: str, entry: dict[str, Any]) -> None:
        require(all(entry[k] is None for k in ("observed_count", "first_observed_ms", "last_observed_ms", "duplicate_timestamps", "expected_count", "missing_count", "expected_count_basis")), "cost unavailable event facts")
        rows = Counter()
        source_days: dict[str, set[str]] = defaultdict(set)
        descriptors = []
        for d, lin in self.cost_by_symbol[symbol]:
            comp = d["component"]
            rows[comp] += d["row_count"]
            for raw in lin.get("raw_objects") or []:
                if raw.get("economic_day") is not None:
                    day = raw["economic_day"]
                    require(date.fromisoformat(day).isoformat() == day, "cost source date")
                    source_days[comp].add(day)
            descriptors.append({"component": comp, "utc_month": d["utc_month"], "row_count": d["row_count"],
                "parquet_bytes": d["parquet_bytes"], "lineage_bytes": d["lineage_bytes"], "descriptor_sha256": sha(canonical(d)),
                "parquet_sha256": d["parquet_sha256"], "lineage_sha256": d["lineage_sha256"],
                "authority": "pinned_cost_completion_descriptor;market_values_not_rescanned"})
        cost_pin = dict((n, h) for n, _, h in self.p.roots)[COST]
        descriptors.append({"completion_sha256": cost_pin, "frozen_source_gap_sha256": self.inputs[COST]["frozen_source_gaps"]["sha256"]})
        units = {"retained_book_depth": "normalized_book_depth_rows", "retained_book_ticker": "normalized_book_ticker_rows", "fee_authority_gap": "authority_gap_rows"}
        require(entry["component_counts"] == [{"component": k, "row_count": v, "unit": units.get(k, "component_native_rows")} for k, v in sorted(rows.items())]
                and entry["source_day_extrema"] == [{"component": k, "first_source_day": min(v), "last_source_day": max(v)} for k, v in sorted(source_days.items())]
                and entry["input_descriptors"] == descriptors, "cost summary accepted descriptors/counts/extrema")
        require(entry["non_instrument_cost_counts"] == {"official_historical_fee_rows": 0, "scenario_policy_rows": 2}
                and entry["fee_authority_gap_reference"] == {"present": True, "authority": "accepted_cost_completion", "historical_fee_observation": False}, "cost summary non-backdated fee evidence")

    def inventory_and_metadata(self) -> list[dict[str, Any]]:
        expected_dirs = {".staging"}
        for rel in self.inventory:
            expected_dirs.update(str(p) for p in Path(rel).parents if str(p) != ".")
        actual_files, actual_dirs = set(), set()
        def walk(directory: int, prefix: Path) -> None:
            with os.scandir(directory) as entries:
                for ent in entries:
                    component(ent.name)
                    relpath = prefix / ent.name
                    rel = str(relpath)
                    require(not ent.is_symlink(), "foreign symlink in coverage tree")
                    if ent.is_dir(follow_symlinks=False):
                        actual_dirs.add(rel)
                        require(rel in expected_dirs, "foreign coverage directory")
                        child = os.open(ent.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                        try:
                            walk(child, relpath)
                        finally:
                            os.close(child)
                    else:
                        require(ent.is_file(follow_symlinks=False), "nonregular coverage entry")
                        require(rel in self.inventory, "foreign coverage file")
                        actual_files.add(rel)
        root = open_directory(self.output)
        try:
            walk(root, Path())
        finally:
            os.close(root)
        require(actual_files == set(self.inventory) and actual_dirs == expected_dirs, "exact coverage file/directory inventory (including staging)")
        staging = open_directory(self.output / ".staging")
        try:
            require(not os.listdir(staging), "nonempty staging")
        finally:
            os.close(staging)
        # Recheck every consumed artifact's inode, size and timestamps before evidence publication.
        for path, snapshot in self.snapshots.items():
            with regular(path) as stream:
                require(fingerprint(os.fstat(stream.fileno())) == snapshot, "authenticated input changed before completion")
        m = self.c["metadata_ledger"]
        p = self.p
        expected = {"source_page_counts": {n: v[3] for n, v in p.bounds}, "page_bytes": p.page_bytes,
            "reserved_debit_bytes": p.metadata_budget, "release_wide_allocation_bytes": p.metadata_release,
            "reserved_release_remainder_bytes": p.metadata_remainder, "measured_category_bytes": dict(self.metadata),
            "measured_metadata_bytes": sum(self.metadata.values()),
            "measured_coverage_reservation_remaining_bytes": p.metadata_budget - sum(self.metadata.values()),
            "unused_coverage_reservation_reallocatable": False, "gap_parquet_charged_as_metadata": False}
        require(m == expected and set(m["measured_category_bytes"]) == CATEGORIES, "measured metadata categories/ledger")
        require(sum(self.metadata.values()) <= p.metadata_budget, "metadata reservation exceeded")
        return [self.inventory[k] for k in sorted(self.inventory)]

    def run(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        self.authorities()
        self.membership_and_source()
        self.accepted_index()
        self.quality_authority()
        self.manifests_and_gaps()
        self.cost()
        self.daily_and_summaries()
        inventory = self.inventory_and_metadata()
        facts = {"coverage_completion_sha256": self.p.completion, "membership_identities": len(self.members),
            "funding_only_identities": sorted(self.funding_only), "excluded_classifications": len(self.rejected),
            "components": self.component_facts, "quality_rows_by_product": dict(self.quality_product_rows),
            "cost_source_gap_rows": self.p.cost_gaps, "cost_component_rows": self.cost_component_rows,
            "historical_fee_observations": 0, "non_backdated_policies": 2, "alignment": self.alignment_facts,
            "metadata_category_bytes": dict(self.metadata), "metadata_bytes": sum(self.metadata.values()),
            "inventory_file_count": len(inventory), "inventory_bytes": sum(r["size"] for r in inventory),
            "authenticated_input_files": len(self.snapshots), "accepted_cost_market_values_rescanned": False}
        return facts, inventory


def safe_destination(path: Path, protected: list[Path]) -> Path:
    path = path.absolute()
    require(".." not in path.parts, "unsafe evidence destination")
    require(not any(path == root or path.is_relative_to(root) for root in protected), "evidence destination inside repository/data inputs")
    require(not path.exists() and not path.is_symlink(), "evidence destination already exists")
    require(path.parent.is_dir(), "evidence parent does not exist")
    for part in (path.parent, *path.parent.parents):
        require(not part.is_symlink(), "evidence destination has symlink ancestor")
    return path


def open_directory(path: Path) -> int:
    """Return a held no-follow descriptor for an absolute directory path."""
    path = path.absolute()
    require(".." not in path.parts, "unsafe evidence parent")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in path.parts[1:]:
            child = os.open(component(name), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def publish_evidence(artifacts: list[tuple[Path, bytes]], protected: list[Path]) -> None:
    """Exclusive publication and rollback use held parent descriptors throughout."""
    parents: dict[Path, int] = {}
    created: list[tuple[int, str, int]] = []
    def verify_parents() -> None:
        for path, held in parents.items():
            current = open_directory(path)
            try:
                a, b = os.fstat(held), os.fstat(current)
                require((a.st_dev, a.st_ino) == (b.st_dev, b.st_ino), "evidence parent was replaced")
            finally:
                os.close(current)
    try:
        for path, _ in artifacts:
            safe_destination(path, protected)
            if path.parent not in parents:
                parents[path.parent] = open_directory(path.parent)
        for path, body in artifacts:
            verify_parents()
            directory = parents[path.parent]
            fd = os.open(component(path.name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory)
            created.append((directory, path.name, os.fstat(fd).st_ino))
            with os.fdopen(fd, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            verify_parents()
        for fd in parents.values():
            os.fsync(fd)
        verify_parents()
    except BaseException:
        for directory, name, inode in reversed(created):
            try:
                facts = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if facts.st_ino == inode and stat.S_ISREG(facts.st_mode):
                    os.unlink(name, dir_fd=directory)
                    os.fsync(directory)
            except FileNotFoundError:
                pass
        raise
    finally:
        for fd in parents.values():
            os.close(fd)


def reconcile(repo_root: Path, output_root: Path, result_path: Path, inventory_path: Path,
              *, _policy: _Policy | None = None, command: list[str] | None = None) -> dict[str, Any]:
    policy = _Policy() if _policy is None else _policy
    repo_root, output_root = repo_root.absolute(), output_root.absolute()
    for root in (repo_root, output_root):
        require(root.is_dir(), "input root missing")
        for part in (root, *root.parents):
            require(not part.is_symlink(), "input root has symlink ancestor")
        require(".." not in root.parts, "unsafe input root")
    require(output_root != repo_root, "coverage root aliases repository")
    protected = [repo_root, output_root]
    result_path = safe_destination(result_path, protected)
    inventory_path = safe_destination(inventory_path, protected)
    require(result_path != inventory_path, "evidence outputs alias")
    started = datetime.now(UTC).isoformat()
    capacity = os.statvfs(output_root)
    facts, rows = Checker(repo_root, output_root, policy).run()
    after_capacity = os.statvfs(output_root)
    inventory_body = b"".join(canonical(row) for row in rows)
    with regular(Path(__file__)) as stream:
        helper_sha = hash_stream(stream)
    result = {"status": "PASS", "exit_code": 0, "command": command if command is not None else list(sys.argv),
        "helper_path": str(Path(__file__).absolute()), "helper_sha256": helper_sha,
        "started_utc": started, "finished_utc": datetime.now(UTC).isoformat(),
        "statvfs_before": {"available_bytes": capacity.f_bavail * capacity.f_frsize,
                           "free_bytes": capacity.f_bfree * capacity.f_frsize},
        "statvfs": {"available_bytes": after_capacity.f_bavail * after_capacity.f_frsize,
                    "free_bytes": after_capacity.f_bfree * after_capacity.f_frsize,
                    "total_bytes": after_capacity.f_blocks * after_capacity.f_frsize, "fragment_size": after_capacity.f_frsize},
        "inventory_path": str(inventory_path), "inventory_sha256": sha(inventory_body), "facts": facts}
    # Inventory first, PASS result last. Handled failure rolls both back using the
    # original directories even when their names have been replaced concurrently.
    publish_evidence([(inventory_path, inventory_body), (result_path, canonical(result))], protected)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo-root", "output-root", "result-path", "inventory-path"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = reconcile(args.repo_root, args.output_root, args.result_path, args.inventory_path,
                           command=[str(Path(__file__)), *(sys.argv[1:] if argv is None else argv)])
    except (ReconciliationError, OSError, ValueError, KeyError, TypeError, pa.ArrowException) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": result["status"], "inventory_sha256": result["inventory_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
