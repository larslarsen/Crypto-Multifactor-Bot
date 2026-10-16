"""Review 483 bounded full-path adversarial evidence fixtures; no real data audit."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/research/reconcile_binance_usdm_coverage.py"
SPEC = importlib.util.spec_from_file_location("coverage_reconciler_under_test", SCRIPT)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
SPEC.loader.exec_module(m)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def digest(body):
    return hashlib.sha256(body).hexdigest()


def schema_fields(schema):
    return [{"name": f.name, "arrow_type": str(f.type), "nullable": f.nullable} for f in schema]


def identity(symbol):
    return {"venue": "BINANCE_USDM", "native_symbol": symbol, "canonical_instrument_id": None,
            "canonical_instrument_version_id": None, "reference_identity_state": "reference_identity_not_yet_created"}


def schema_hash(product):
    value = {"required_product": product, "schema": schema_fields(m.final_product_schema(product))}
    return digest((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def filler(field):
    if field.nullable:
        return None
    t = field.type
    if pa.types.is_dictionary(t) or pa.types.is_string(t):
        return "fixture"
    if pa.types.is_boolean(t):
        return False
    if pa.types.is_decimal(t):
        return Decimal(1)
    if pa.types.is_list(t):
        return []
    return 1


class Fixture:
    """Build honest accepted input evidence and independently specified coverage claims.

    Deliberate mutations are applied before hashing, so failures cannot be satisfied by
    checking content addresses alone. No producer validator or constructor is imported.
    """
    def __init__(self, tmp, *, daily_mutation=None, summary_mutation=None,
                 manifest_mutation=None, completion_mutation=None, input_mutation=None,
                 gap_mutation=None, authority_mutation=None, accepted_mutation=None,
                 physical_mutation=None):
        self.physical_mutation = physical_mutation
        self.repo = tmp / "repo"
        self.out = self.repo / "data/coverage"
        self.repo.mkdir()
        self.out.mkdir(parents=True)
        (self.out / ".staging").mkdir()
        self.result = tmp / "result.json"
        self.inventory = tmp / "inventory.jsonl"
        self.metadata = Counter({k: 0 for k in m.CATEGORIES})
        self.members = ["0GUSDT", "FUNDONLY", "ROWLESS"]
        self.month = "2025-09"
        self.input_roots = {p: self.repo / ("data/price/" + p if p in (m.INDIC, m.BASIS) else "data/" + p) for p in (*m.SUMMARY, m.MEMBER)}
        self.descriptor_roots = {p: root.parent if p in (m.INDIC, m.BASIS) else root for p, root in self.input_roots.items()}
        self.completions = {}
        self.pins = {}
        self.input_rows = {}
        self.partitions = {p: [] for p in m.TIMESTAMPS}
        self.source = {**identity("0GUSDT"), "required_product": m.BAR, "family_group": "klines",
            "families": ["monthly/klines"], "family_count": 1, "gap_kind": "head_gap_pre_listing",
            "gap_status": "head_gap_pre_listing", "blocking": False, "observed_months": 1,
            "first_observed_period": self.month, "last_observed_period": self.month,
            "family_first_observed_period": self.month, "family_last_observed_period": self.month,
            "onboard_period": self.month, "close_period": "", "missing_months": [],
            "missing_month_count": 0, "objects": 1, "explained_by": "fixture"}
        classifications = []
        for symbol in self.members:
            evidence = ({"kind": "official_realized_funding_observation", "semantics": "only a perpetual contract realizes funding",
                         "families": ["monthly/fundingRate"], "example_key": "funding/example.zip"} if symbol == "FUNDONLY" else
                        {"kind": "authenticated_current_exchange_info", "endpoint": "https://example.invalid",
                         "contract_type": "PERPETUAL", "base_asset": "X", "quote_asset": "USDT", "margin_asset": "USDT",
                         "onboard_ms": self.ms(1)})
            classifications.append({"symbol": symbol, "accepted": True, "membership_class": "confirmed_perpetual", "evidence": [evidence]})
        rejected = [{"symbol": "EXCLUDED", "accepted": False, "membership_class": "unsupported"}]
        gap = {"symbol": "0GUSDT", "family_group": "klines", "families": ["monthly/klines"],
               "kind": "head_gap_pre_listing", "status": "head_gap_pre_listing", "blocking": False,
               "observed_months": 1, "first_observed": self.month, "last_observed": self.month,
               "family_first_observed": self.month, "family_last_observed": self.month,
               "onboard_period": self.month, "missing_months": [], "missing_month_count": 0, "objects": 1, "explained_by": "fixture"}
        report = {"membership": {"classifications": classifications + rejected},
                  "product_matrix": [{"product": m.BAR, "universe_coverage_gaps": [gap], "typed_gap_symbols": ["ROWLESS"]}]}
        if authority_mutation:
            authority_mutation(report)
        report_pin = self.authority("report.json", report)
        source_path = self.repo / "producer.py"
        source_path.write_text("# pinned producer fixture\n")
        producer_pin = ("producer.py", digest(source_path.read_bytes()))
        holdout_pin = self.authority("holdout.json", {"boundary_id": "fixture_boundary", "boundary_utc": "2026-08-21T16:19:08.994166+00:00"})
        bounds = (("source_gap", (1, 1, 1, 1, 1000000, 1000000)),
                  ("typed_gap", (1, 1, 1, 1, 1000000, 1000000)),
                  ("quality_gap", (1, 1, 100, 2, 1000000, 1000000)))
        sizing = {"coverage_authority": {}, "capacity": {"catalog_manifest_bundle_bytes": 5000000},
                  "partitioning": {"catalog_page_bytes": 1000000}}
        for name, b in bounds:
            sizing["coverage_authority"][m.COMPONENTS[name] + "_component"] = {
                "schema": schema_fields(m.SCHEMAS[name]), "projected_rows": b[2], "partition_count": b[3],
                "projected_bytes": b[4], "largest_partition_bytes": b[5]}
        sizing_pin = self.authority("sizing.json", sizing)
        # Membership records authenticate exact authority classifications, including a
        # rowless detailed identity and one independently classified funding-only identity.
        member_parts = []
        for r in classifications:
            symbol = r["symbol"]
            schema = m.final_product_schema(m.MEMBER)
            row = {f.name: filler(f) for f in schema}
            row.update(identity(symbol))
            row.update({"membership_class": "confirmed_perpetual", "contract_type": "PERPETUAL",
                        "contract_metadata_state": "funding_only_terms_unavailable" if symbol == "FUNDONLY" else "exchange_info_terms_available"})
            d = self.input_partition(m.MEMBER, symbol, None, [row], {"classification_sha256": digest(encoded(r))})
            member_parts.append(d)
        membership = {"required_product": m.MEMBER, "schema_sha256": schema_hash(m.MEMBER), "partitions": member_parts,
                      "membership_rows": 3, "detailed_metadata_rows": 2, "funding_only_rows": 1, "excluded_classifications": 1,
                      "row_equation": {"classifications": 4, "accepted_membership_rows": 3, "excluded_classifications": 1}}
        self.save_input_completion(m.MEMBER, membership)
        # Nine observed days. Native OI phase is deliberately 7 milliseconds past the
        # UTC grid; September 22 has fourteen basis rows and is the only partial day.
        for p, column in m.TIMESTAMPS.items():
            for symbol in ("0GUSDT", "FUNDONLY"):
                stamps = []
                if symbol == "0GUSDT":
                    for day in range(22, 31):
                        n = 14 if p == m.BASIS and day == 22 else 288 if p == m.OI else 24 if p in m.FIXED else 1
                        stamps += [self.ms(day) + i * (300000 if p == m.OI else 3600000) + (7 if p == m.OI else 0) for i in range(n)]
                elif p == m.FUND:
                    stamps = [self.ms(22)]
                if not stamps:
                    continue
                if input_mutation:
                    input_mutation(p, symbol, stamps)
                schema = m.final_product_schema(p)
                rows = []
                for timestamp in stamps:
                    row = {f.name: filler(f) for f in schema}
                    row.update(identity(symbol))
                    row[column] = timestamp
                    rows.append(row)
                self.input_rows[p, symbol] = stamps
                self.partitions[p].append(self.input_partition(p, symbol, self.month, rows))
        quality_row = {**identity("0GUSDT"), "required_product": m.BASIS, "utc_month": self.month,
                       "missing_run_start_ms": self.ms(22) + 14 * 3600000, "missing_run_end_ms": self.ms(22) + 23 * 3600000,
                       "expected_grid_count": 10, "gap_kind": "unjoinable_source", "reason": "fixture"}
        quality_descriptor = self.input_partition(m.BASIS, "0GUSDT", self.month, [quality_row], quality=True)
        for p in m.TIMESTAMPS:
            n = sum(len(v) for (pp, _), v in self.input_rows.items() if pp == p)
            equation = self.equation(p, n)
            c = {"required_product": p, "schema_sha256": schema_hash(p), "partitions": self.partitions[p]}
            c["totals" if p == m.OI else "row_equation"] = equation
            if p == m.LIQ:
                c["gaps"] = []
            if p == m.BASIS:
                c["quality_gap_artifacts"] = [quality_descriptor]
            if accepted_mutation:
                accepted_mutation(p, c)
            self.save_input_completion(p, c)
        self.cost_descriptors = []
        self.cost_lineages = {}
        for symbol in self.members:
            self.cost_partition("fee_authority_gap", symbol, "authority", 1)
        self.cost_partition("retained_book_ticker", "0GUSDT", self.month, 123,
                            raw_objects=[{"economic_day": "2025-09-22"}, {"economic_day": "2025-09-30"}])
        self.cost_partition("official_fee_schedule", "__schema__", "schema", 0)
        self.cost_partition("scenario_policy", "BINANCE_USDM", "configuration", 2)
        frozen_body = encoded({"gaps": [{"symbol": "ROWLESS", "kind": "cost_sample_unavailable"}]})
        frozen_sha = digest(frozen_body)
        frozen_path = f".source-gaps/{frozen_sha}.json"
        self.write(self.input_roots[m.COST] / frozen_path, frozen_body)
        cost = {"required_product": m.COST, "partitions": self.cost_descriptors,
                "frozen_source_gaps": {"path": frozen_path, "sha256": frozen_sha, "bytes": len(frozen_body), "row_count": 1},
                "fee_authority": {"gap_rows": 3, "official_historical_rows": 0, "missing_fee_is_zero": False},
                "scenario_policy": {"rows": 2, "historical_observation": False, "historical_upper_bound": False,
                                    "charges_each_side": True, "authority_class": "ASSUMED_CONSERVATIVE", "policy_known_at": "2026-08-23T03:00:00Z"},
                "component_rows": {"fee_authority_gap": 3, "retained_book_ticker": 123, "scenario_policy": 2, "official_fee_schedule": 0},
                "source_equation": {"objects": 1, "generation0_objects": 1, "recovery_objects": 0,
                                    "physical_rows": 123, "retained_rows": 123, "deduplicated_rows": 0, "dropped_rows": 0}}
        self.save_input_completion(m.COST, cost)
        self.manifest_rows = {k: [] for k in ("source_gap", "typed_gap", "quality_gap", "daily", "summary", "excluded_membership")}
        self.coverage_gap("source_gap", m.BAR, "0GUSDT", "authority", [self.source],
                    [{"report_sha256": report_pin[1], "rows_sha256": digest(encoded([self.source]))}], gap_mutation)
        typed_raw = {"required_product": m.BAR, "native_symbol": "ROWLESS"}
        self.coverage_gap("typed_gap", m.BAR, "ROWLESS", "authority", [{**identity("ROWLESS"), "required_product": m.BAR}],
                          [{"report_sha256": report_pin[1], "row_sha256": digest(encoded(typed_raw))}], gap_mutation)
        self.coverage_gap("quality_gap", m.BASIS, "0GUSDT", self.month, [quality_row],
            [{"descriptor_sha256": digest(encoded(quality_descriptor)), "parquet_sha256": quality_descriptor["parquet_sha256"],
              "lineage_sha256": quality_descriptor["lineage_sha256"], "first_source_row_ordinal": 0,
              "last_source_row_ordinal": 0, "source_row_count": 1}], gap_mutation)
        all_hash, observed_hash, full_hash = (hashlib.sha256() for _ in range(3))
        observed_total = full_total = 0
        for symbol in self.members:
            report_days = []
            for day in range(1, 31):
                day_text = f"2025-09-{day:02}"
                active = symbol == "0GUSDT" and day >= 22
                counts = ([24, 288, 1, 14 if day == 22 else 24, 1] if active else
                          [0, 0, 1, 0, 0] if symbol == "FUNDONLY" and day == 22 else [0] * 5)
                present = [n > 0 for n in counts]
                complete = [active, active, None, active and day != 22, None]
                exclusions = []
                for i, p in enumerate(m.ALIGN):
                    has_partition = (p, symbol) in self.input_rows
                    exclusions.append(None if present[i] and (p not in m.FIXED or complete[i]) else
                                      5 if present[i] else 1 if has_partition and p == m.FUND else
                                      2 if has_partition and p == m.LIQ else 0 if has_partition else
                                      3 if p == m.BAR and symbol == "ROWLESS" else 4)
                row = [day_text, counts, present, complete, exclusions, all(present), active and day > 22]
                report_days.append(row)
            document = {"document_type": "binance_usdm_coverage_daily_alignment", "schema_version": 1,
                "native_symbol": symbol, "utc_month": self.month, "field_order": list(m.FIELD_ORDER),
                "product_order": list(m.ALIGN), "exclusion_reason_dictionary": dict(m.REASONS), "semantics": dict(m.SEMANTICS),
                "days": report_days, "counts": {"days": 30, "five_product_observed_intersection": 9 if symbol == "0GUSDT" else 0,
                                               "full_cadence_with_event_presence": 8 if symbol == "0GUSDT" else 0}}
            if daily_mutation:
                daily_mutation(document)
            # Recompute claimed digests from even the deliberately altered document.
            for row in document["days"]:
                b = encoded([symbol, row])
                all_hash.update(b)
                if row[5]:
                    observed_hash.update(b)
                    observed_total += 1
                if row[6]:
                    full_hash.update(b)
                    full_total += 1
            d = self.coverage_json(f".daily/{symbol}/{self.month}", document, "daily-alignment")
            self.manifest_rows["daily"].append({"native_symbol": symbol, "utc_month": self.month, **d, **document["counts"]})
        for symbol in self.members:
            entries = []
            for p in m.SUMMARY:
                stamps = self.input_rows.get((p, symbol), [])
                cost_product = p == m.COST
                missing = 10 if p == m.BASIS and symbol == "0GUSDT" else 0
                countable = (bool(stamps) or missing > 0) and (p in m.FIXED or p == m.LIQ)
                context = ({k: self.source[k] for k in ("gap_kind", "gap_status", "first_observed_period", "last_observed_period",
                           "family_first_observed_period", "family_last_observed_period", "onboard_period", "close_period", "missing_months")}
                           if p == m.BAR and symbol == "0GUSDT" else None)
                row_sha = digest(encoded(self.source))
                if context is not None:
                    context.update({"row_sha256": row_sha, "semantics": "qualification_gap_context;not_a_current_missing_observation"})
                refs = [{"utc_month": d["utc_month"], "descriptor_sha256": digest(encoded(d)),
                         "parquet_sha256": d["parquet_sha256"], "lineage_sha256": d["lineage_sha256"]}
                        for d in self.partitions.get(p, []) if d["native_symbol"] == symbol]
                components = None
                extrema = None
                if cost_product:
                    chosen = [d for d in self.cost_descriptors if d["native_symbol"] == symbol]
                    refs = [{"component": d["component"], "utc_month": d["utc_month"], "row_count": d["row_count"],
                        "parquet_bytes": d["parquet_bytes"], "lineage_bytes": d["lineage_bytes"], "descriptor_sha256": digest(encoded(d)),
                        "parquet_sha256": d["parquet_sha256"], "lineage_sha256": d["lineage_sha256"],
                        "authority": "pinned_cost_completion_descriptor;market_values_not_rescanned"} for d in chosen]
                    refs.append({"completion_sha256": self.pins[m.COST], "frozen_source_gap_sha256": frozen_sha})
                    components = [{"component": d["component"], "row_count": d["row_count"],
                                   "unit": "authority_gap_rows" if d["component"] == "fee_authority_gap" else "normalized_book_ticker_rows"}
                                  for d in sorted(chosen, key=lambda d: d["component"])]
                    extrema = ([{"component": "retained_book_ticker", "first_source_day": "2025-09-22", "last_source_day": "2025-09-30"}]
                               if symbol == "0GUSDT" else [])
                entry = {"required_product": p, "observed_count": None if cost_product else len(stamps),
                    "first_observed_ms": min(stamps) if stamps else None, "last_observed_ms": max(stamps) if stamps else None,
                    "duplicate_timestamps": None if cost_product else len(stamps) - len(set(stamps)), "input_descriptors": refs,
                    "expected_count": len(stamps) + missing if countable else None, "missing_count": missing if countable else None,
                    "expected_count_basis": "accepted_observed_rows_plus_normalized_quality_gap_expected_grid_count" if countable and p in m.FIXED else
                        "authenticated_inclusive_request_calendar;never_a_completeness_claim" if countable else None,
                    "time_precision": "source_day_only_event_extrema_unavailable" if cost_product else "millisecond_native_five_minute_phase" if p == m.OI else
                        "millisecond_observed_event" if p == m.FUND else "millisecond_observed_daily_point" if p == m.LIQ else "millisecond_hour_open",
                    "observed_count_unit": "unavailable_per_instrument;component_counts_only" if cost_product else "normalized_rows",
                    "component_counts": components, "source_day_extrema": extrema,
                    "non_instrument_cost_counts": {"official_historical_fee_rows": 0, "scenario_policy_rows": 2} if cost_product else None,
                    "fee_authority_gap_reference": {"present": True, "authority": "accepted_cost_completion", "historical_fee_observation": False} if cost_product else None,
                    "source_gap_row_sha256": [row_sha] if context is not None else [],
                    "qualification_source_gap_context": [context] if context is not None else [],
                    "quality_gap_partitions": [{k: v for k, v in self.manifest_rows["quality_gap"][0].items() if k not in ("required_product", "native_symbol")}]
                        if p == m.BASIS and symbol == "0GUSDT" else [],
                    "source_revisions": "retained_in_referenced_partition_lineages;no_availability_vintage_inferred"}
                entries.append(entry)
            doc = {"document_type": "binance_usdm_instrument_coverage_summary", "schema_version": 1, **identity(symbol),
                   "reporting_domain": {"first_utc_month": self.month, "last_utc_month": self.month}, "products": entries}
            if summary_mutation:
                summary_mutation(doc)
            d = self.coverage_json(f".summary/{symbol}", doc, "coverage-summary")
            self.manifest_rows["summary"].append({"native_symbol": symbol, **d})
        self.manifest_rows["excluded_membership"] = rejected
        if manifest_mutation:
            manifest_mutation(self.manifest_rows)
        manifests = {}
        for name, rows in self.manifest_rows.items():
            doc = {"document_type": f"binance_usdm_coverage_{name}_manifest", "schema_version": 1, "row_count": len(rows), "rows": rows}
            manifests[name] = self.coverage_json(".manifests", doc, name, path=True)
        components = {}
        for name, b in bounds:
            rows = self.manifest_rows[name]
            schema_value = schema_fields(m.SCHEMAS[name])
            schema_sha = (digest((json.dumps({"required_product": m.COVER, "schema": schema_value}, indent=2, sort_keys=True) + "\n").encode())
                          if name == "source_gap" else digest(encoded(schema_value)))
            components[m.COMPONENTS[name]] = {"schema_sha256": schema_sha, "rows": b[0], "partitions": b[1],
                "parquet_bytes": sum(d["parquet_bytes"] for d in rows), "largest_file_bytes": max(d["parquet_bytes"] for d in rows),
                "bound_bytes": b[4], "largest_file_bound_bytes": b[5], "manifest_sha256": manifests[name]["sha256"],
                **({"row_ceiling": b[2], "partition_ceiling": b[3]} if name == "quality_gap" else {"partition_bound": b[3]})}
        components["cost_normalization_source_gap_reference"] = {"rows": 1, "sha256": frozen_sha, "bytes": len(frozen_body), "copied": False,
            "semantics": "accepted_normalization_source_gaps_distinct_from_qualification_source_gaps"}
        components["fee_authority_gap_reference"] = {"rows": 3, "copied": False, "completion_sha256": self.pins[m.COST],
            "semantics": "historical_fee_schedule_unavailable;not_zero_cost"}
        completion = {"document_type": "binance_usdm_coverage_gap_product_completion", "schema_version": 1,
            "required_product": m.COVER, "normalizer_source_sha256": producer_pin[1],
            "authorities": {"report_sha256": report_pin[1], "sizing_sha256": sizing_pin[1], "holdout_sha256": holdout_pin[1],
                            "holdout_boundary_id": "fixture_boundary", "holdout_utc": "2026-08-21T16:19:08.994166+00:00"},
            "input_completions": {p: {"completion_sha256": h} for p, h in self.pins.items()}, "manifests": manifests,
            "membership": {"accepted_identities": 3, "funding_only_identities": 1, "excluded_classifications": 1, "product_absence_removes_membership": False},
            "components": components, "row_equations": {p: c.get("row_equation", c.get("totals", c.get("source_equation"))) for p, c in self.completions.items()},
            "alignment": {"historical_domain": {"first_utc_month": self.month, "last_utc_month": self.month, "month_count": 1,
                "basis": "accepted_source_membership_bounds_and_actual_product_ranges"},
                "daily_report_equation": {"accepted_membership_identities": 3, "historical_utc_months": 1, "expected_partitions": 3, "published_partitions": 3},
                "daily_report_partitions": 3, "aligned_day_rows": 90, "five_product_observed_day_count": observed_total,
                "full_cadence_day_count": full_total, "aligned_days_sha256": all_hash.hexdigest(),
                "five_product_observed_day_sha256": observed_hash.hexdigest(), "full_cadence_day_sha256": full_hash.hexdigest(),
                "maximum_loaded_symbol_month_observations": 2592, "funding_expected_count": None, "liquidation_complete": False,
                "daily_manifest_sha256": manifests["daily"]["sha256"], "summary_manifest_sha256": manifests["summary"]["sha256"]},
            "metadata_ledger": {"source_page_counts": {n: b[3] for n, b in bounds}, "page_bytes": 1000000,
                "reserved_debit_bytes": 4000000, "release_wide_allocation_bytes": 5000000, "reserved_release_remainder_bytes": 1000000,
                "unused_coverage_reservation_reallocatable": False, "gap_parquet_charged_as_metadata": False}}
        self.seal(completion, completion_mutation)
        self.policy = replace(m._Policy(), completion=self.coverage_pin, report=report_pin, sizing=sizing_pin, holdout=holdout_pin,
            source=producer_pin, holdout_id="fixture_boundary", roots=tuple((p, str(self.input_roots[p].relative_to(self.repo)), h) for p, h in self.pins.items()),
            bounds=bounds, quality_rows=((m.BASIS, 1),), members=3, funding_only=1, excluded=1, cost_gaps=1,
            metadata_budget=4000000, metadata_release=5000000, metadata_remainder=1000000, page_bytes=1000000, totals=(3, 90, 9, 8))

    @staticmethod
    def ms(day):
        return int(datetime(2025, 9, day, tzinfo=UTC).timestamp()) * 1000

    @staticmethod
    def write(path, body):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    def authority(self, path, value):
        body = encoded(value)
        self.write(self.repo / path, body)
        return path, digest(body)

    def input_partition(self, product, symbol, month, rows, extra=None, quality=False):
        root = self.descriptor_roots[product]
        schema = m.SCHEMAS["quality_gap"] if quality else m.final_product_schema(product)
        table = pa.Table.from_pylist(rows, schema=schema)
        if self.physical_mutation and not quality:
            table = self.physical_mutation(product, table)
        sink = pa.BufferOutputStream()
        pq.write_table(table, sink)
        body = sink.getvalue().to_pybytes()
        h = digest(body)
        sub = f"quality/{h}.parquet" if quality else f"parts/{symbol}/{month or 'authority'}/{h}.parquet"
        self.write(root / sub, body)
        lin = {"required_product": product, "native_symbol": symbol, "row_count": len(rows), "parquet_sha256": h, **(extra or {})}
        if month:
            lin["utc_month"] = month
        lb = encoded(lin)
        lh = digest(lb)
        lp = f"lineage/{lh}.json"
        self.write(root / lp, lb)
        d = {"native_symbol": symbol, "row_count": len(rows), "parquet_path": sub, "parquet_sha256": h,
             "lineage_path": lp, "lineage_sha256": lh}
        if month:
            d["utc_month"] = month
        return d

    def save_input_completion(self, product, value):
        body = encoded(value)
        h = digest(body)
        self.write(self.input_roots[product] / ".complete" / (h + ".json"), body)
        self.pins[product] = h
        self.completions[product] = value

    def cost_partition(self, comp, symbol, month, rows, **extra):
        # No cost Parquet fixture exists. A full-path success proves it was never read.
        h = digest((comp + symbol).encode())
        lin = {"required_product": m.COST, "native_symbol": symbol, "utc_month": month,
               "component": comp, "row_count": rows, "parquet_sha256": h, **extra}
        lb = encoded(lin)
        lh = digest(lb)
        lp = f"lineage/{lh}.json"
        self.write(self.input_roots[m.COST] / lp, lb)
        d = {"component": comp, "native_symbol": symbol, "utc_month": month, "row_count": rows,
             "parquet_path": f"parts/{comp}/{symbol}/{h}.parquet", "parquet_sha256": h, "parquet_bytes": 100,
             "lineage_path": lp, "lineage_sha256": lh, "lineage_bytes": len(lb)}
        self.cost_descriptors.append(d)
        self.cost_lineages[lh] = lin

    @staticmethod
    def equation(p, n):
        if p in (m.BAR, m.FLOW):
            return {"physical_rows": n, "product_rows": n, "excluded_rows": 0, "collapsed_rows": 0, "duplicate_rows": 0, "overlap_rows": 0}
        if p in (m.INDIC, m.BASIS):
            k = 3 if p == m.BASIS else 1
            return {"physical_source_rows": n * k, "product_rows": n, "joined_input_rows": n * k,
                    "unjoinable_source_rows": 0, "excluded_source_rows": 0, "collapsed_identical_rows": 0, "fabricated_rows": 0}
        r = {"physical_source_rows": n, "product_rows": n, "excluded_source_rows": 0,
             "collapsed_identical_source_rows" if p == m.OI else "collapsed_identical_rows": 0}
        if p == m.FUND:
            r.update({"inferred_events": 0, "conflicting_events": 0})
        if p == m.LIQ:
            r.update({"inclusive_requested_slots": n, "missing_daily_slots": 0, "imputed_rows": 0})
        return r

    def coverage_json(self, directory, value, category, path=False):
        body = encoded(value)
        h = digest(body)
        rel = directory + "/" + h + ".json"
        self.write(self.out / rel, body)
        self.metadata[category] += len(body)
        return {"sha256": h, "bytes": len(body), **({"path": rel} if path else {})}

    def coverage_gap(self, name, product, symbol, month, rows, upstream, mutation):
        directory = m.DIRECTORIES[name]
        sink = pa.BufferOutputStream()
        pq.write_table(pa.Table.from_pylist(rows, schema=m.SCHEMAS[name]), sink)
        body = sink.getvalue().to_pybytes()
        h = digest(body)
        self.write(self.out / f".{directory}/{product}/{symbol}/{month}/{h}.parquet", body)
        lin = {"document_type": f"binance_usdm_coverage_{directory}_lineage", "schema_version": 1,
            "component": directory, "required_product": product, "native_symbol": symbol, "utc_month": month,
            "row_count": len(rows), "parquet_sha256": h, "schema": schema_fields(m.SCHEMAS[name]), "upstream": upstream}
        if mutation:
            mutation(name, lin)
        ld = self.coverage_json(f".{directory}-lineage/{product}/{symbol}/{month}", lin, directory + "-lineage")
        d = {"required_product": product, "native_symbol": symbol, "row_count": len(rows), "parquet_sha256": h,
             "parquet_bytes": len(body), "lineage_sha256": ld["sha256"], "lineage_bytes": ld["bytes"]}
        if name == "quality_gap":
            d["utc_month"] = month
        self.manifest_rows[name].append(d)
        return d

    def seal(self, completion, mutation):
        n = 0
        for _ in range(32):
            cats = dict(self.metadata)
            cats["completion"] = n
            completion["metadata_ledger"].update({"measured_category_bytes": cats, "measured_metadata_bytes": sum(cats.values()),
                "measured_coverage_reservation_remaining_bytes": 4000000 - sum(cats.values())})
            if mutation:
                mutation(completion)
            body = encoded(completion)
            if len(body) == n:
                break
            n = len(body)
        self.coverage_pin = digest(body)
        self.write(self.out / ".complete" / (self.coverage_pin + ".json"), body)

    def run(self):
        return m.reconcile(self.repo, self.out, self.result, self.inventory, _policy=self.policy, command=["fixture"])


def expect_failure(fixture, message=None):
    with pytest.raises((m.ReconciliationError, OSError, ValueError, KeyError), match=message):
        fixture.run()
    assert not fixture.result.exists()
    assert not fixture.inventory.exists()


def test_complete_audit_serializes_authenticated_inventory_and_native_phase(tmp_path):
    f = Fixture(tmp_path)
    result = f.run()
    assert result == json.loads(f.result.read_bytes())
    assert result["status"] == "PASS"
    rows = [json.loads(line) for line in f.inventory.read_bytes().splitlines()]
    assert [r["relative_path"] for r in rows] == sorted(str(p.relative_to(f.out)) for p in f.out.rglob("*") if p.is_file())
    assert digest(f.inventory.read_bytes()) == result["inventory_sha256"]
    for row in rows:
        p = f.out / row["relative_path"]
        s = p.stat()
        assert row == {"relative_path": str(p.relative_to(f.out)), "sha256": digest(p.read_bytes()),
                       "size": s.st_size, "inode": s.st_ino, "mtime_ns": s.st_mtime_ns}
    facts = result["facts"]
    assert facts["alignment"]["reference_example"]["basis_rows"] == 14
    assert facts["alignment"]["counts"] == [3, 90, 9, 8]
    assert facts["funding_only_identities"] == ["FUNDONLY"]
    assert facts["accepted_cost_market_values_rescanned"] is False
    assert result["statvfs"]["available_bytes"] > 0
    # Source schema survives list<item> -> list<element> display differences.
    p = next((f.out / ".source-gaps").rglob("*.parquet"))
    assert pq.ParquetFile(p).schema_arrow.equals(m.SCHEMAS["source_gap"])
    assert m.schema_identity("source_gap") != digest(encoded(schema_fields(m.SCHEMAS["source_gap"])))


@pytest.mark.parametrize("kind", ["presence", "cadence", "event_complete", "exclusion", "observed", "full", "duplicate_day", "missing_day", "unsorted_days"])
def test_resigned_daily_semantics_refused(tmp_path, kind):
    def mutation(doc):
        if doc["native_symbol"] != "0GUSDT":
            return
        row = doc["days"][21]
        if kind == "presence":
            row[2][0] = False
        if kind == "cadence":
            row[3][3] = True
        if kind == "event_complete":
            row[3][2] = True
        if kind == "exclusion":
            row[4][3] = None
        if kind == "observed":
            row[5] = False
        if kind == "full":
            row[6] = True
        if kind == "duplicate_day":
            doc["days"][1] = doc["days"][0]
        if kind == "missing_day":
            doc["days"].pop()
        if kind == "unsorted_days":
            doc["days"].reverse()
    expect_failure(Fixture(tmp_path, daily_mutation=mutation), "daily|calendar")


@pytest.mark.parametrize("kind", ["observed_count", "first_observed_ms", "last_observed_ms", "duplicate_timestamps", "input_descriptors",
                                  "source_gap_row_sha256", "qualification_source_gap_context", "expected_count", "quality_gap_partitions",
                                  "funding_expected", "cost_counts", "cost_extrema", "cost_fees", "product_order"])
def test_resigned_summaries_refused(tmp_path, kind):
    def mutation(doc):
        if doc["native_symbol"] != "0GUSDT":
            return
        bar, basis, cost = doc["products"][0], doc["products"][5], doc["products"][-1]
        if kind in ("observed_count", "first_observed_ms", "last_observed_ms", "duplicate_timestamps"):
            bar[kind] += 1
        elif kind == "input_descriptors":
            bar[kind][0]["descriptor_sha256"] = "0" * 64
        elif kind == "source_gap_row_sha256":
            bar[kind] = []
        elif kind == "qualification_source_gap_context":
            bar[kind][0]["gap_kind"] = "invented"
        elif kind == "expected_count":
            bar[kind] += 1
        elif kind == "quality_gap_partitions":
            basis[kind] = []
        elif kind == "funding_expected":
            doc["products"][3]["expected_count"] = 27
        elif kind == "cost_counts":
            cost["component_counts"][0]["row_count"] += 1
        elif kind == "cost_extrema":
            cost["source_day_extrema"][0]["first_source_day"] = "2025-09-23"
        elif kind == "cost_fees":
            cost["non_instrument_cost_counts"]["official_historical_fee_rows"] = 1
        elif kind == "product_order":
            doc["products"].reverse()
    expect_failure(Fixture(tmp_path, summary_mutation=mutation), "summary|references|product")


@pytest.mark.parametrize("kind", ["authority", "input_binding", "source", "schema_envelope", "metadata_categories", "metadata_measurement", "reservation", "cost_reference"])
def test_resigned_completion_refused(tmp_path, kind):
    def mutation(c):
        if kind == "authority":
            c["authorities"]["report_sha256"] = "0" * 64
        if kind == "input_binding":
            c["input_completions"][m.BAR]["completion_sha256"] = "0" * 64
        if kind == "source":
            c["normalizer_source_sha256"] = "0" * 64
        if kind == "schema_envelope":
            c["components"]["source_gap"]["schema_sha256"] = digest(encoded(schema_fields(m.SCHEMAS["source_gap"])))
        if kind == "metadata_categories":
            c["metadata_ledger"]["measured_category_bytes"]["invented"] = 0
        if kind == "metadata_measurement":
            cats = c["metadata_ledger"]["measured_category_bytes"]
            cats["daily"] += 1
            cats["summary"] -= 1
        if kind == "reservation":
            c["metadata_ledger"]["reserved_release_remainder_bytes"] += 1
        if kind == "cost_reference":
            c["components"]["cost_normalization_source_gap_reference"]["rows"] = 2
    expect_failure(Fixture(tmp_path, completion_mutation=mutation))


@pytest.mark.parametrize("kind", ["daily_duplicate", "daily_missing", "daily_order", "summary_member", "gap_duplicate", "excluded"])
def test_resigned_manifest_sets_refused(tmp_path, kind):
    def mutation(rows):
        if kind == "daily_duplicate":
            rows["daily"][1] = rows["daily"][0]
        if kind == "daily_missing":
            rows["daily"].pop()
        if kind == "daily_order":
            rows["daily"].reverse()
        if kind == "summary_member":
            rows["summary"][2]["native_symbol"] = "FOREIGN"
        if kind == "gap_duplicate":
            rows["source_gap"].append(dict(rows["source_gap"][0]))
        if kind == "excluded":
            rows["excluded_membership"] = []
    expect_failure(Fixture(tmp_path, manifest_mutation=mutation))


@pytest.mark.parametrize("kind", ["lineage_schema", "lineage_product", "quality_upstream"])
def test_resigned_gap_lineage_refused(tmp_path, kind):
    def mutation(name, lin):
        if kind == "lineage_schema" and name == "source_gap":
            lin["schema"][0]["nullable"] = True
        if kind == "lineage_product" and name == "typed_gap":
            lin["required_product"] = m.COVER
        if kind == "quality_upstream" and name == "quality_gap":
            lin["upstream"][0]["source_row_count"] = 2
    expect_failure(Fixture(tmp_path, gap_mutation=mutation), "lineage")


@pytest.mark.parametrize("kind", ["foreign_file", "foreign_directory", "missing_staging", "symlink", "fifo", "extra_completion"])
def test_exact_inventory_and_regular_entries(tmp_path, kind):
    f = Fixture(tmp_path)
    if kind == "foreign_file":
        (f.out / "foreign").write_text("x")
    if kind == "foreign_directory":
        (f.out / "foreign").mkdir()
    if kind == "missing_staging":
        (f.out / ".staging").rmdir()
    if kind == "symlink":
        (f.out / "foreign").symlink_to(f.repo / "report.json")
    if kind == "fifo":
        os.mkfifo(f.out / "foreign")
    if kind == "extra_completion":
        (f.out / ".complete/extra.json").write_text("{}")
    expect_failure(f)


@pytest.mark.parametrize("kind", ["inside_repo", "inside_data", "same_output", "existing", "symlink_parent"])
def test_output_safety_no_artifacts(tmp_path, kind):
    f = Fixture(tmp_path)
    if kind == "inside_repo":
        f.result = f.repo / "result.json"
    if kind == "inside_data":
        f.result = f.out / "result.json"
    if kind == "same_output":
        f.result = f.inventory
    if kind == "existing":
        f.result.write_text("preserve")
        with pytest.raises(m.ReconciliationError, match="exists"):
            f.run()
        assert f.result.read_text() == "preserve"
        assert not f.inventory.exists()
        return
    if kind == "symlink_parent":
        link = tmp_path / "link"
        link.symlink_to(tmp_path, target_is_directory=True)
        f.result = link / "new.json"
    expect_failure(f)


@pytest.mark.parametrize("unsafe", ["../outside.json", "/absolute.json", "a//b", "./same", "a\\b"])
def test_manifest_unsafe_reference_through_complete_audit(tmp_path, unsafe):
    def mutation(c):
        c["manifests"]["daily"]["path"] = unsafe
    expect_failure(Fixture(tmp_path, completion_mutation=mutation), "unsafe")


def test_input_pin_does_not_accept_mutated_file(tmp_path):
    f = Fixture(tmp_path)
    (f.repo / "report.json").write_text("{}")
    expect_failure(f, "digest")


def test_source_symlink_cannot_be_authenticated(tmp_path):
    f = Fixture(tmp_path)
    source = f.repo / "producer.py"
    copy = tmp_path / "producer-copy.py"
    copy.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(copy)
    expect_failure(f)


@pytest.mark.parametrize("kind", ["duplicate", "traversal"])
def test_accepted_descriptor_paths_are_checked_before_consumption(tmp_path, kind):
    def mutation(product, completion):
        if kind == "duplicate" and product == m.FUND:
            completion["partitions"][1]["parquet_path"] = completion["partitions"][0]["parquet_path"]
        if kind == "traversal" and product == m.BAR:
            completion["partitions"][0]["parquet_path"] = "../foreign.parquet"
    expect_failure(Fixture(tmp_path, accepted_mutation=mutation), "duplicate accepted|unsafe")


@pytest.mark.parametrize("kind", ["schema", "row_count"])
def test_authenticated_input_physical_contract_is_independent(tmp_path, kind):
    def mutation(product, table):
        if product != m.BAR:
            return table
        if kind == "row_count":
            return table.slice(0, table.num_rows - 1)
        fields = list(table.schema)
        fields[0] = fields[0].with_nullable(True)
        return table.cast(pa.schema(fields))
    expect_failure(Fixture(tmp_path, physical_mutation=mutation), "physical Arrow|physical row")


def test_corrupt_accepted_timestamp_parquet_is_not_footer_trusted(tmp_path):
    f = Fixture(tmp_path)
    d = f.partitions[m.BAR][0]
    p = f.descriptor_roots[m.BAR] / d["parquet_path"]
    body = bytearray(p.read_bytes())
    body[8] ^= 1
    p.write_bytes(body)
    expect_failure(f, "digest")


@pytest.mark.parametrize("kind", ["duplicate", "irregular"])
def test_cadence_recomputed_from_authenticated_input_timestamps(tmp_path, kind):
    def mutation(p, symbol, stamps):
        if p == m.OI and symbol == "0GUSDT":
            if kind == "duplicate":
                stamps[1] = stamps[0]
            else:
                stamps[1] += 1
    expect_failure(Fixture(tmp_path, input_mutation=mutation), "independent")


def test_membership_funding_only_authority_is_independent_of_row_absence(tmp_path):
    def mutation(report):
        report["membership"]["classifications"][1]["evidence"][0]["kind"] = "invented"
    expect_failure(Fixture(tmp_path, authority_mutation=mutation), "funding-only")


def test_cli_has_no_pin_or_validation_relaxation_flags(capsys):
    with pytest.raises(SystemExit) as raised:
        m.main(["--repo-root", "/tmp", "--output-root", "/tmp", "--result-path", "/tmp/a",
                "--inventory-path", "/tmp/b", "--completion", "0" * 64])
    assert raised.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err


def test_cli_failure_is_nonzero_without_pass_evidence(tmp_path, capsys):
    f = Fixture(tmp_path)
    assert m.main(["--repo-root", str(f.repo), "--output-root", str(f.out),
                   "--result-path", str(f.result), "--inventory-path", str(f.inventory)]) == 1
    captured = capsys.readouterr()
    assert "FAIL" in captured.err and "PASS" not in captured.out
    assert not f.result.exists() and not f.inventory.exists()


def test_publication_ancestor_swap_cannot_redirect_writes(tmp_path, monkeypatch):
    f = Fixture(tmp_path)
    parent = tmp_path / "evidence"
    parent.mkdir()
    moved = tmp_path / "displaced-evidence"
    f.result, f.inventory = parent / "result.json", parent / "inventory.jsonl"
    original = os.open
    swapped = False
    def swapping_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if flags & os.O_CREAT and not swapped:
            swapped = True
            parent.rename(moved)
            parent.symlink_to(f.repo, target_is_directory=True)
        return original(path, flags, mode, dir_fd=dir_fd)
    monkeypatch.setattr(m.os, "open", swapping_open)
    expect_failure(f)
    assert swapped
    assert list(moved.iterdir()) == []
    assert not (f.repo / "result.json").exists()
    assert not (f.repo / "inventory.jsonl").exists()


def test_publication_second_create_failure_rolls_back_inventory(tmp_path, monkeypatch):
    f = Fixture(tmp_path)
    original = os.open
    creations = 0
    def failing_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal creations
        if flags & os.O_CREAT:
            creations += 1
            if creations == 2:
                raise OSError("fixture second creation failure")
        return original(path, flags, mode, dir_fd=dir_fd)
    monkeypatch.setattr(m.os, "open", failing_open)
    expect_failure(f, "second creation")
    assert creations == 2
